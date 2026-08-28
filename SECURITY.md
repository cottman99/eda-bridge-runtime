# Security

Do not place EDA license strings, SSH private keys, bridge authentication
tokens, customer designs, or customer paths in requests or ledger metadata.
The runtime redacts common secret-shaped keys before persistence, but callers
remain responsible for using artifact references instead of embedding private
payloads.

Report security issues privately to the repository owner. Do not open a public
issue containing credentials, proprietary design data, or host inventories.

