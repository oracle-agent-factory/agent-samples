# Agent catalog

Samples are organized first by the business application they integrate with, then by use case:

```text
agents/
└── <application>/
    └── <use-case>/
```

Each use-case directory contains one reviewable Agent Builder workflow, its archive metadata, a complete `sample.json` documentation manifest, supporting assets, and demo material. Generated `.paf` archives are release assets and are not committed.

## Applications

- [JD Edwards EnterpriseOne](jd-edwards/)

Application and use-case slugs in `sample.json` must match their directory names. The agent `slug` remains independent and determines the stable release asset filename.
