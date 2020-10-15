# pynetdicom_scp

## Getting started

Use <code>.env_sample</code> as a template to create a .env file in the same
directory as Dockerfile

Run
```
>> docker-compose build
>> docker-compose up
```

Uses
...
Starts a DICOM-compliant listener with port/AE_TITLE as specified in .env
Receives DICOMs to dcmstore/received
Once study has completed transfer, moves to dcmstore/queue.

"Completed transfer" is defined as >=2 minutes since last image received for
a given MRN/Acc #, or since container up for orphaned studies already in
/received folder on container up.

Intended use is to then monitor dcmstore/queue for new studies and trigger
some downstream processing step. Sample hook for that step included but this
repo does not include any actual processing from the queue. After
processing study is moved from dcmstore/queue => dcmstore/processed
