# CSAF v2.1 csd04 excerpt

Lines 1404 to 1418 of csaf-v2.1-csd04.md (published 22 October 2026), with a
plain fence after them for contrast.

### 2.4.4 Content Schema<a id='content-schema'></a>

An extension SHALL contain exactly the following elements:
CSAF Extension Schema (`$schema`), Extension Category (`category`), Critical (`critical`) and Content (`content`).

```yaml <!--json-path($.properties)-->
$schema: String
category: String.Enum
content: Mapping
critical: Boolean
```

> The CSAF Extension Content Schema works an interface definition.
> It is used in the CSAF Schema and defines a common structure for all CSAF Extensions.

```json
{"category": "csaf_base"}
```
