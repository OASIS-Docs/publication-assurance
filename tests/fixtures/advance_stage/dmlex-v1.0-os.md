![OASIS Logo](https://docs.oasis-open.org/templates/OASISLogo-v3.0.png)

---

# Data Model for Lexicography (DMLex) Version 1.0

## OASIS Standard

## 29 April 2025

#### This stage:

https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html \
https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.pdf (Authoritative)

#### Previous stage:

https://docs.oasis-open.org/lexidma/dmlex/v1.0/cs01/dmlex-v1.0-cs01.html \
https://docs.oasis-open.org/lexidma/dmlex/v1.0/cs01/dmlex-v1.0-cs01.pdf (Authoritative)

#### Latest stage:

https://docs.oasis-open.org/lexidma/dmlex/v1.0/dmlex-v1.0.html \
https://docs.oasis-open.org/lexidma/dmlex/v1.0/dmlex-v1.0.pdf (Authoritative)

#### Technical Committee:

[OASIS Lexicographic Infrastructure Data Model and API (LEXIDMA) TC](http://www.oasis-open.org/committees/lexidma/)

#### Chair:

Michal Měchura (michmech@mail.muni.cz), [Masaryk University](http://www.ijs.si/)

#### Editors:

David Filip (glorfindel@mail.muni.cz), [Masaryk University](https://www.muni.cz/) \
Miloš Jakubíček (milos.jakubicek@sketchengine.eu), [Lexical Computing](http://www.lexicalcomputing.com/) \
Vojtěch Kovář (vojcek@mail.muni.cz), [Masaryk University](https://www.muni.cz/) \
Simon Krek (simon.krek@ijs.si), [Jozef Stefan Institute](http://www.ijs.si/) \
John McCrae (john.mccrae@universityofgalway.ie), [University of Galway](https://www.universityofgalway.ie/) \
Michal Měchura (michmech@mail.muni.cz), [Masaryk University](https://www.muni.cz/)

#### Additional artifacts:

This prose specification is one component of a Work Product that also includes declarative validation artifacts accessible from <https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/>:

- XML: <https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/XML/>

- JSON: <https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/JSON/>

- RDF: <https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/RDF/>

Informative copies of third party schemas are provided:

<https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/informativeCopiesOf3rdPartySchemas/>

#### Declared namespaces: <a id='namespaces'></a>

This specification declares one or more namespaces. Namespace isn't considered an XML specific feature in this serialization independent specification.

**The core and modules namespace**

- <http://docs.oasis-open.org/lexidma/ns/dmlex-1.0>

#### Abstract:

This document defines the 1st version of a data model in support of the high-priority technical goals described in the LEXIDMA TC's charter, including:

- A serialization-independent Data Model for Lexicography (DMLex)

- An XML serialization of DMLex

- A JSON serialization of DMLex

- A relational database serialization of DMLex

- An RDF serialization of DMLex

- An informative NVH serialization of DMLex

#### Status:

This document was last revised or approved by the LEXIDMA TC on the above date. The level of approval is also listed above. Check the "Latest version" location noted above for possible later revisions of this document. Any other numbered Versions and other technical work produced by the Technical Committee (TC) are listed at <https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=lexidma#technical>.

TC members should send comments on this document to the TC's email list. Others should send comments to the TC's public comment list, after subscribing to it by following the instructions at the "[Send A Comment](https://www.oasis-open.org/committees/comments/index.php?wg_abbrev=lexidma)" button on the TC's web page at <https://www.oasis-open.org/committees/lexidma/>.

This specification is provided under the [Non-Assertion](https://www.oasis-open.org/policies-guidelines/ipr/#Non-Assertion-Mode) Mode of the [OASIS IPR Policy](https://www.oasis-open.org/policies-guidelines/ipr/), the mode chosen when the Technical Committee was established. For information on whether any patents have been disclosed that may be essential to implementing this specification, and any offers of patent licensing terms, please refer to the Intellectual Property Rights section of the TC's web page (<https://www.oasis-open.org/committees/lexidma/ipr.php>).

Note that any machine-readable content ([Computer Language Definitions](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/#wpComponentsCompLang)) declared Normative for this Work Product is provided in separate plain text files. In the event of a discrepancy between any such plain text file and display content in the Work Product's prose narrative document(s), the content in the separate plain text file prevails.

#### Key words:

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as described in [BCP 14](https://tools.ietf.org/html/bcp14) \[[RFC2119](#rfc2119)\] and \[[RFC8174](#rfc8174)\] if, and only if, they appear in all capitals, as shown here.

#### Citation format:

When referencing this specification the following citation format should be used:

\[DMLex-1.0\]

*Data Model for Lexicography Version 1.0*. Edited by David Filip, Miloš Jakubíček, Simon Krek, John McCrae, and Michal Měchura. 29 April 2025. OASIS OASIS Standard. <https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html>. Latest version: <https://docs.oasis-open.org/lexidma/dmlex/v1.0/dmlex-v1.0.html>.

---

## Notices

Copyright © OASIS Open 2025.

All Rights Reserved.Distributed under the terms of the OASIS [IPR Policy](https://www.oasis-open.org/policies-guidelines/ipr/).

The name "OASIS" is a trademark of [OASIS](https://www.oasis-open.org/), the owner and developer of this specification, and should be used only to refer to the organization and its official outputs.

For complete copyright information please see the [full Notices](#full-notices) section in an Appendix below.

---

# Appendix C Machine Readable Validation Artifacts (Normative) <a id='Validation'></a>

- [XML schema](https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/XML/dmlex.xsd)

- [XML schema excluding the cross-lingual module](https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/XML/dmlex_no-crosslingual.xsd)

- [JSON schema](https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/JSON/dmlex.schema.json)

- [JSON schema excluding the cross-lingual module](https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/JSON/dmlex_no-crosslingual.schema.json)

- [NVH schema (informative)](https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/schemas/informativeCopiesOf3rdPartySchemas/NVH/dmlex.nvh)

# Appendix D DMLex UML diagram (Normative) <a id='diagram_uml'></a>


### F.1.2 Tracking of changes made in response to Public Reviews <a id='f-1-2-tracking-of-changes-made-in-response-to-public-reviews'></a>

This is to facilitate human tracking of changes in the specification made since the first Public Review publication on 8th September 2023.

#### F.1.2.1 Tracking of changes in response to the 4th Public Review <a id='csprd04'></a>

This section tracks major changes made to this specification compared to the Committee Specification Draft 04 [https://docs.oasis-open.org/lexidma/dmlex/v1.0/csd04/dmlex-v1.0-csd04.pdf.pdf](https://docs.oasis-open.org/lexidma/dmlex/v1.0/csd04/dmlex-v1.0-csd04.pdf). The fourth Public Review took place from 10 September 2024 until 11 October 2024.

1. No changes were made except administratively progressiong the draft to Committee Specification.

#### F.1.2.2 Tracking of changes in response to the 3rd Public Review <a id='csprd03'></a>

This section tracks major changes made to this specification compared to the Committee Specification Draft 03 [https://docs.oasis-open.org/lexidma/dmlex/v1.0/csd03/dmlex-v1.0-csd03.pdf.pdf](https://docs.oasis-open.org/lexidma/dmlex/v1.0/csd03/dmlex-v1.0-csd03.pdf). The third Public Review took place from 28 June 2024 until 27 July 2024.

1. The `sameAs` object has been added as property of `etymonLanguage` and `etymonType` (GitHub issue [140](https://github.com/oasis-tcs/lexidma/issues/140)).

2. The `translation` property of `etymon` has been removed (GitHub issue [139](https://github.com/oasis-tcs/lexidma/issues/139)).

3. The XSD schema has been updated to accept entries, senses and collocate markers without an `id` attribute. (GitHub issue [135](https://github.com/oasis-tcs/lexidma/issues/135)).

#### F.1.2.3 Tracking of changes in response to the 2nd Public Review <a id='csprd02'></a>

This section tracks major changes made to this specification compared to the Committee Specification Draft 02 <https://docs.oasis-open.org/lexidma/dmlex/v1.0/csd02/dmlex-v1.0-csd02.pdf>. The second Public Review took place from 31st January 2024 until 29th February 2024.

1. A method for constructing fragment identification strings has been added to the specification (GitHub issue [97](https://github.com/oasis-tcs/lexidma/issues/97)).

