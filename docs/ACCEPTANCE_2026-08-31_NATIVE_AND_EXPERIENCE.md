# Governed native execution and bootstrap experience acceptance

Date: 2026-08-31 (Asia/Shanghai)

This acceptance used only sanitized synthetic fixtures on the configured Linux
EDA host and `DISPLAY=:4.0`. It did not use customer projects, solve, GUI
automation, or publish vendor documentation.

## Ansys Electronics Desktop 2026 R1

The Agent first verified the official PyAEDT `VariableManager.set_variable`
signature, then submitted official Python through `eda.native-batch/v1`.

| Gate | Retained result |
| --- | --- |
| Observe | Run `run_a1bc0505ff0643038df05f3837bee9fd`; opened the exact HFSS 3D Layout design, returned `Setup1`, preserved the source, and returned the Bridge-computed bundle fingerprint in 22.721 s adapter time |
| Staged mutation | Run `run_d29a5b7daea249d1ab8aaf519416ef11`; set one design variable to `1mm` in staging through official PyAEDT, saved and closed, opened a new AEDT session, read back exactly `1mm`, preserved the source, and promoted only a new output in 42.568 s adapter time |

The observe source fingerprint was
`532d2dcc8296b9c6afda52a33a8513c92cacc6339bc57ca56dc4a81d857cd246`.
The promoted output fingerprint was
`142f360f85b9a39c57370d3ba76d4db3dd5d790bf23374f6e56ad998bcb6ff77`.

## ADS 2026 Update 2.1

The Agent retrieved version-matched local documentation for
`open_workspace`, `active_workspace`, and `workspace_is_open`, then generated
official ADS Python for the exact installation.

| Gate | Retained result |
| --- | --- |
| Experience gateway | Run `run_f659ecec70a04bf589d8380943bc4a62`; returned one matching hashed DDS experience asset over the normal SSH Runtime path without launching ADS |
| Observe | Run `run_339f24277aac4148b7cfbe8493063340`; opened a staged copy through official ADS Python, returned `opened=true`, preserved the source, and returned its fingerprint in 0.750 s client wall time |
| Staged mutation | Run `run_1f45a5191b7f408cb5508c778500cc8f`; created a new library and schematic through official ADS Python in staging, closed the first process, reopened the design in a separate ADS Python process, validated it, preserved the source, and promoted only a new workspace in 1.438 s client wall time |

The observe source fingerprint was
`a40aefd8a05963947a6745731340f5a02b605402e35d6c66b4e38fccdb067c9d`.
The promoted output fingerprint was
`abb0584b1509e371ed99888af822e9e389120c25e9879e368db362f3695a2cba`.

## Boundary proved

These runs prove exact-context official Python reach, declared source/write
scope, content fingerprints, non-overwriting staging, total timeout, separate
validation process/session, source preservation, and promotion after
validation. They do not prove a hostile-code sandbox or every official API.

The packaged experience assets are advisory. Compiled shortcuts are preferred
only while their asset id, version, content hash, applicability, parameters,
validation, and runtime state match. Without a shortcut or experience asset,
the governed native path remains available.
