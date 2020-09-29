# ref https://pydicom.github.io/pynetdicom/dev/tutorials/create_scp.html

import os
from datetime import datetime
import logging
import threading
from pathlib import Path
from pydicom.filewriter import write_file_meta_info
from pynetdicom import (
  AE, debug_logger, evt, AllStoragePresentationContexts,
  ALL_TRANSFER_SYNTAXES
)

debug_logger()
LOGGER = logging.getLogger('pynetdicom')

"""
dict where
  key: 'received/{mrn}/{accnum}'
  val: datetime obj of last received file from {key} study
"""
study_progress = {}

def check_studies():
  """
  Checks for studies where no new images have been received in at least 2 min
  Assume these stale studies have completed sending
  Move from received => queue folder for further processing
  """
  threading.Timer(20.0, check_studies).start()
  stale_studies = [s for s in study_progress if (datetime.now() - study_progress[s]).total_seconds() >= 120]
  for old in stale_studies:
    new = 'dcmstore/queue'/old.relative_to('dcmstore/received')
    new.mkdir(parents=True, exist_ok=True)
    old.rename(new)
    study_progress.pop(old)
    try:
      old.parent.rmdir()
    except OSError:
      """Dir not empty"""

check_studies()

def handle_store_flat_dir(event, storage_dir):
  """Handle EVT_C_STORE events."""
  try:
    storage_dir.mkdir(parents=True, exist_ok=True)
  except:
    # Unable to create output dir, return failure status
    return 0xC001

  # We rely on the UID from the C-STORE request instead of decoding
  # This is faster than decoding the file to read the UID, but
  # if you do decode you can use MRN, acc#, etc for more useful dir tree
  fname = storage_dir/event.request.AffectedSOPInstanceUID
  with open(fname, 'wb') as f:
    # Write the preamble, prefix and file meta information elements
    f.write(b'\x00' * 128)
    f.write(b'DICM')
    write_file_meta_info(f, event.file_meta)
    # Write the raw encoded dataset
    f.write(event.request.DataSet.getvalue())

    return 0x0000

def handle_store_pt_accnum_dir(event, storage_dir):
  """Handle EVT_C_STORE events."""
  ds = event.dataset
  ds.file_meta = event.file_meta
  save_loc = storage_dir/ds.PatientID/ds.AccessionNumber
  try:
    save_loc.mkdir(parents=True, exist_ok=True)
  except:
    # Unable to create output dir, return failure status
    return 0xC001
  study_progress[save_loc] = datetime.now()
  save_loc = save_loc/ds.SOPInstanceUID
  ds.save_as(save_loc.with_suffix(save_loc.suffix+'.dcm'), write_like_original=False)

  return 0x0000

handlers = [
  (evt.EVT_C_STORE, handle_store_pt_accnum_dir, [Path('dcmstore/received')]),
]

ae = AE()
storage_sop_classes = [
  cx.abstract_syntax for cx in AllStoragePresentationContexts
]
for uid in storage_sop_classes:
  ae.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)

# Supposedly increases transfer speed
# ref: https://pydicom.github.io/pynetdicom/dev/examples/storage.html#storage-scp
ae.maximum_pdu_size = 0

ae.start_server(('', 11112), block=True, ae_title=os.environ['AE_TITLE'], evt_handlers=handlers)