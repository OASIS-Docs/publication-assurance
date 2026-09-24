
![OASIS Logo](https://docs.oasis-open.org/templates/OASISLogo-v3.0.png)

-------

# OData Extension for Data Aggregation Version 4.0

## Committee Specification 04

## 18 November 2025

&nbsp;

#### This stage:
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs04/odata-data-aggregation-ext-v4.0-cs04.md (Authoritative) \
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs04/odata-data-aggregation-ext-v4.0-cs04.html \
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs04/odata-data-aggregation-ext-v4.0-cs04.pdf

#### Previous stage:
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs03/odata-data-aggregation-ext-v4.0-cs03.md (Authoritative) \
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs03/odata-data-aggregation-ext-v4.0-cs03.html \
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs03/odata-data-aggregation-ext-v4.0-cs03.pdf

#### Latest stage:
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/odata-data-aggregation-ext-v4.0.md (Authoritative) \
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/odata-data-aggregation-ext-v4.0.html \
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/odata-data-aggregation-ext-v4.0.pdf

#### Technical Committee:
[OASIS Open Data Protocol (OData) TC](https://www.oasis-open.org/committees/odata/)

#### Chairs:

Ralf Handl (ralf.handl@sap.com), [SAP SE](https://www.sap.com/) \
Michael Pizzo (mikep@microsoft.com), [Microsoft](https://www.microsoft.com/)

#### Editors:

Ralf Handl (ralf.handl@sap.com), [SAP SE](https://www.sap.com/) \
Hubert Heijkers (hubert.heijkers@nl.ibm.com), [IBM](https://www.ibm.com/) \
Gerald Krause (gerald.krause@sap.com), [SAP SE](https://www.sap.com/) \
Michael Pizzo (mikep@microsoft.com), [Microsoft](https://www.microsoft.com/) \
Heiko Theißen (heiko.theissen@sap.com), [SAP SE](https://www.sap.com/) \
Martin Zurmuehl (martin.zurmuehl@sap.com), [SAP SE](https://www.sap.com/)

#### [Additional artifacts:]{id=AdditionalArtifacts}
This document is one component of a Work Product that also includes:
* ABNF components: _OData Aggregation ABNF Construction Rules Version 4.0 and OData Aggregation ABNF Test Cases_: https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs04/abnf/
* OData Aggregation Vocabulary:
  * https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs04/vocabularies/Org.OData.Aggregation.V1.json
  * https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs04/vocabularies/Org.OData.Aggregation.V1.xml

#### [Related work:]{id=RelatedWork}
This specification is related to:
* _OData Version 4.01_. Edited by Michael Pizzo, Ralf Handl, and Martin Zurmuehl. A multi-part Work Product which includes:
  * _OData Version 4.01 Part 1: Protocol_. Latest stage: https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part1-protocol.html
  * _OData Version 4.01 Part 2: URL Conventions_. Latest stage: https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part2-url-conventions.html
  * _ABNF components: OData ABNF Construction Rules Version 4.01 and OData ABNF Test Cases_. https://docs.oasis-open.org/odata/odata/v4.01/os/abnf/
* _OData Vocabularies Version 4.0_. Edited by Michael Pizzo, Ralf Handl, and Ram Jeyaraman. Latest stage: https://docs.oasis-open.org/odata/odata-vocabularies/v4.0/odata-vocabularies-v4.0.html
* _OData Common Schema Definition Language (CSDL) JSON Representation Version 4.01_. Edited by Michael Pizzo, Ralf Handl, and Martin Zurmuehl. Latest stage: https://docs.oasis-open.org/odata/odata-csdl-json/v4.01/odata-csdl-json-v4.01.html
* _OData Common Schema Definition Language (CSDL) XML Representation Version 4.01_. Edited by Michael Pizzo, Ralf Handl, and Martin Zurmuehl. Latest stage: https://docs.oasis-open.org/odata/odata-csdl-xml/v4.01/odata-csdl-xml-v4.01.html
* _OData JSON Format Version 4.01_. Edited by Ralf Handl, Mike Pizzo, and Mark Biamonte. Latest stage: https://docs.oasis-open.org/odata/odata-json-format/v4.01/odata-json-format-v4.01.html

#### Abstract:
This specification adds basic grouping and aggregation functionality (e.g. sum, min, and max) to the Open Data Protocol (OData) without changing any of the base principles of OData.

#### Status:
This document was last revised or approved by the OASIS Open Data Protocol (OData) TC on the above date. The level of approval is also listed above. Check the "Latest stage" location noted above for possible later revisions of this document. Any other numbered Versions and other technical work produced by the Technical Committee (TC) are listed at https://groups.oasis-open.org/communities/tc-community-home2?CommunityKey=e7cac2a9-2d18-4640-b94d-018dc7d3f0e2#technical.

TC members should send comments on this specification to the TC's email list. Any individual may submit comments to the TC by sending email to Technical-Committee-Comments@oasis-open.org. Please use a Subject line like "Comment on OData Data Aggregation".

This specification is provided under the [RF on RAND Terms Mode](https://www.oasis-open.org/policies-guidelines/ipr/#RF-on-RAND-Mode) of the [OASIS IPR Policy](https://www.oasis-open.org/policies-guidelines/ipr/), the mode chosen when the Technical Committee was established. For information on whether any patents have been disclosed that may be essential to implementing this specification, and any offers of patent licensing terms, please refer to the Intellectual Property Rights section of the TC's web page (https://www.oasis-open.org/committees/odata/ipr.php).

Note that any machine-readable content ([Computer Language Definitions](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/#wpComponentsCompLang)) declared Normative for this Work Product is provided in separate plain text files. In the event of a discrepancy between any such plain text file and display content in the Work Product's prose narrative document(s), the content in the separate plain text file prevails.

#### Key words:
The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119](#rfc2119) and [RFC8174](#rfc8174) when, and only when, they appear in all capitals, as shown here.

#### Citation format:
When referencing this specification the following citation format should be used:

**[OData-Data-Agg-v4.0]**

_OData Extension for Data Aggregation Version 4.0_.
Edited by Ralf Handl, Hubert Heijkers, Gerald Krause, Michael Pizzo, Heiko Theißen, and Martin Zurmuehl. 18 November 2025. OASIS Committee Specification 04.
https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/cs04/odata-data-aggregation-ext-v4.0-cs04.html.
Latest stage: https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/odata-data-aggregation-ext-v4.0.html.

#### Notices
Copyright © OASIS Open 2025. All Rights Reserved.

Distributed under the terms of the OASIS [IPR Policy](https://www.oasis-open.org/policies-guidelines/ipr/).

The name "OASIS" is a trademark of [OASIS](https://www.oasis-open.org/), the owner and developer of this specification, and should be used only to refer to the organization and its official outputs.

For complete copyright information please see the full Notices section in an Appendix [below](#Notices).

-------


The ABNF rules [OData-ABNF](#ODataABNF) have been simplified in this version to reflect these restrictions. Also, some members of the OData Aggregation Vocabulary [OData-VocAggr](#ODataVocAggr) have been omitted from this version. These members are referenced by **[OData-Data-Agg-v4.0]** OASIS Committee Specification 03 but not by this version.

<!--
Here is a customized command line which will generate HTML from the markdown file (named `odata-data-aggregation-ext-v4.0-cs04.md`). Line breaks are added for readability only:

```
pandoc -f gfm+tex_math_dollars+fenced_divs+smart
       -t html
       -o odata-data-aggregation-ext-v4.0-cs04.html
       -c styles/markdown-styles-v1.7.3b.css
       -c styles/odata.css
       -s
       --mathjax
       --eol=lf
       --wrap=none
       --metadata pagetitle="OData Extension for Data Aggregation Version 4.0"
       odata-data-aggregation-ext-v4.0-cs04.md
```

This uses pandoc 3.1.13 from https://github.com/jgm/pandoc/releases/tag/3.1.13.

<edmx:Edmx xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx"
           Version="4.0">
  <edmx:Reference Uri="https://docs.oasis-open.org/odata/odata-data-
    aggregation-ext/v4.0/cs04/vocabularies/Org.OData.Aggregation.V1.xml">
    <edmx:Include Alias="Aggregation"
                  Namespace="Org.OData.Aggregation.V1" />
  </edmx:Reference>
