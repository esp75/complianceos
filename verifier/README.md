# ComplianceOS verifier

A single-file, offline checker for signed dossiers (`dossier-signed.json`) and signed program
history exports. It does not need ComplianceOS, a server or a network.

```
pip install cryptography
python complianceos_verify.py dossier-signed.json --fingerprint <signer fingerprint>
python complianceos_verify.py history.json --fingerprint <fp> --previous earlier-history.json
```

Get the fingerprint from the operator by a channel you trust. The file carries its own public key,
so without a pinned fingerprint the check proves only that the file is unchanged. Exit code 2 means
exactly that.
