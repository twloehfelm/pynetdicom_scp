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
  val: datetime of last received file
"""
last_received_time = {}

def check_studies():
  """
  Checks q20sec for studies with no new images in at least 2 min
  Assume these stale studies have finished being sent
  Move from received => queue folder for further processing
  Remove empty dirs from received folder
  """
  threading.Timer(20.0, check_studies).start()
  stale_studies = [s for s in last_received_time if (datetime.now() - last_received_time[s]).total_seconds() >= 120]
  for old in stale_studies:
    new = 'dcmstore/queue'/old.relative_to('dcmstore/received')
    new.mkdir(parents=True, exist_ok=True)
    old.rename(new)
    last_received_time.pop(old)
    try:
      old.parent.rmdir()
    except OSError:
      """
      Dir not empty. Do nothing. The server may be receiving another study from
        the same patient and that study might still be in progress
      """

# Start timed function
check_studies()

def handle_store(event, storage_dir):
  """
  Handle EVT_C_STORE events
  Saves to:
    dcmstore/
      received/
        {mrn}/
          {accnum}/
            {series num}_{series desc}/
              {SOPInstanceUID}.dcm
  """
  ds = event.dataset
  ds.file_meta = event.file_meta
  save_loc = storage_dir/ds.PatientID/ds.AccessionNumber
  last_received_time[save_loc] = datetime.now()
  series_desc = str(ds.SeriesNumber).zfill(2) + '_' + ds.SeriesDescription.replace('/','_')
  save_loc = storage_dir/ds.PatientID/ds.AccessionNumber/series_desc
  try:
    save_loc.mkdir(parents=True, exist_ok=True)
  except:
    # Unable to create output dir, return failure status
    return 0xC001

  save_loc = save_loc/ds.SOPInstanceUID
  # Because SOPInstanceUID includes several '.' you can't just use
  #   with_suffix or else it will replaces the portion of the UID that follows
  #   the last '.' with '.dcm', truncating the actual UID
  save_loc = save_loc.with_suffix(save_loc.suffix +'.dcm')
  ds.save_as(save_loc, write_like_original=False)

  return 0x0000

# List of event handlers
handlers = [
  (evt.EVT_C_STORE, handle_store, [Path('dcmstore/received')]),
]

ae = AE()

# Accept storage of all SOP classes
storage_sop_classes = [
  cx.abstract_syntax for cx in AllStoragePresentationContexts
]
for uid in storage_sop_classes:
  ae.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)

# Supposedly increases transfer speed
# ref: https://pydicom.github.io/pynetdicom/dev/examples/storage.html#storage-scp
ae.maximum_pdu_size = 0

ae.start_server(
  ('', 11112), # Start server on localhost port 11112
  block=True,  # Socket operates in blocking mode
  ae_title=os.environ['AE_TITLE'],
  evt_handlers=handlers
)