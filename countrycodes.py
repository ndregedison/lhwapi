# coding: utf-8

import pyexcel as pe

countrycodes = """Afghanistan,AF,AFG,AFGHANISTAN
Albania,AL,ALB,ALBANIA
Algeria,DZ,DZA,ALGERIA
American Samoa,AS,ASM,AMERICAN SAMOA
Andorra,AD,AND,ANDORRA
Angola,AO,AGO,ANGOLA
Anguilla,AI,AIA,ANGUILLA
Antarctica,AQ,ATA,ANTARCTICA
Antigua and Barbuda,AG,ATG,ANTIGUA AND BARBUDA
Argentina,AR,ARG,ARGENTINA
Armenia,AM,ARM,ARMENIA
Aruba,AW,ABW,ARUBA
Australia,AU,AUS,AUSTRALIA
Austria,AT,AUT,AUSTRIA
Azerbaijan,AZ,AZE,AZERBAIJAN
Bahamas,BS,BHS,BAHAMAS
Bahrain,BH,BHR,BAHRAIN
Bangladesh,BD,BGD,BANGLADESH
Barbados,BB,BRB,BARBADOS
Belarus,BY,BLR,BELARUS
Belgium,BE,BEL,BELGIUM
Belize,BZ,BLZ,BELIZE
Benin,BJ,BEN,BENIN
Bermuda,BM,BMU,BERMUDA
Bhutan,BT,BTN,BHUTAN
Bolivia (Plurinational State of),BO,BOL,BOLIVIA (PLURINATIONAL STATE OF)
"Bonaire, Sint Eustatius and Saba",BQ,BES,"BONAIRE, SINT EUSTATIUS AND SABA"
Bosnia and Herzegovina,BA,BIH,BOSNIA AND HERZEGOVINA
Botswana,BW,BWA,BOTSWANA
Bouvet Island,BV,BVT,BOUVET ISLAND
Brazil,BR,BRA,BRAZIL
British Indian Ocean Territory,IO,IOT,BRITISH INDIAN OCEAN TERRITORY
British Virgin Islands,VG,VGB,VIRGIN ISLANDS (BRITISH)
Brunei Darussalam,BN,BRN,BRUNEI DARUSSALAM
Bulgaria,BG,BGR,BULGARIA
Burkina Faso,BF,BFA,BURKINA FASO
Burundi,BI,BDI,BURUNDI
Cabo Verde,CV,CPV,CABO VERDE
Cambodia,KH,KHM,CAMBODIA
Cameroon,CM,CMR,CAMEROON
Canada,CA,CAN,CANADA
Cayman Islands,KY,CYM,CAYMAN ISLANDS
Central African Republic,CF,CAF,CENTRAL AFRICAN REPUBLIC
Chad,TD,TCD,CHAD
Chile,CL,CHL,CHILE
China,CN,CHN,CHINA
"China, Hong Kong Special Administrative Region",HK,HKG,HONG KONG
"China, Macao Special Administrative Region",MO,MAC,MACAO
Christmas Island,CX,CXR,CHRISTMAS ISLAND
Cocos (Keeling) Islands,CC,CCK,COCOS (KEELING) ISLANDS
Colombia,CO,COL,COLOMBIA
Comoros,KM,COM,COMOROS
Congo,CG,COG,CONGO
Cook Islands,CK,COK,COOK ISLANDS
Costa Rica,CR,CRI,COSTA RICA
Croatia,HR,HRV,CROATIA
Cuba,CU,CUB,CUBA
Curaçao,CW,CUW,CURAÇAO
Cyprus,CY,CYP,CYPRUS
Czechia,CZ,CZE,CZECHIA
Côte d'Ivoire,CI,CIV,CÔTE D'IVOIRE
Democratic People's Republic of Korea,KP,PRK,KOREA (THE DEMOCRATIC PEOPLE’S REPUBLIC OF)
Democratic Republic of the Congo,CD,COD,CONGO (THE DEMOCRATIC REPUBLIC OF THE)
Denmark,DK,DNK,DENMARK
Djibouti,DJ,DJI,DJIBOUTI
Dominica,DM,DMA,DOMINICA
Dominican Republic,DO,DOM,DOMINICAN REPUBLIC
Ecuador,EC,ECU,ECUADOR
Egypt,EG,EGY,EGYPT
El Salvador,SV,SLV,EL SALVADOR
Equatorial Guinea,GQ,GNQ,EQUATORIAL GUINEA
Eritrea,ER,ERI,ERITREA
Estonia,EE,EST,ESTONIA
Ethiopia,ET,ETH,ETHIOPIA
Falkland Islands (Malvinas),FK,FLK,
Faroe Islands,FO,FRO,FAROE ISLANDS
Fiji,FJ,FJI,FIJI
Finland,FI,FIN,FINLAND
France,FR,FRA,FRANCE
French Guiana,GF,GUF,FRENCH GUIANA
French Polynesia,PF,PYF,FRENCH POLYNESIA
French Southern Territories,TF,ATF,FRENCH SOUTHERN TERRITORIES
Gabon,GA,GAB,GABON
Gambia,GM,GMB,GAMBIA
Georgia,GE,GEO,GEORGIA
Germany,DE,DEU,GERMANY
Ghana,GH,GHA,GHANA
Gibraltar,GI,GIB,GIBRALTAR
Greece,GR,GRC,GREECE
Greenland,GL,GRL,GREENLAND
Grenada,GD,GRD,GRENADA
Guadeloupe,GP,GLP,GUADELOUPE
Guam,GU,GUM,GUAM
Guatemala,GT,GTM,GUATEMALA
Guernsey,GG,GGY,GUERNSEY
Guinea,GN,GIN,GUINEA
Guinea-Bissau,GW,GNB,GUINEA-BISSAU
Guyana,GY,GUY,GUYANA
Haiti,HT,HTI,HAITI
Heard Island and McDonald Islands,HM,HMD,HEARD ISLAND AND MCDONALD ISLANDS
Holy See,VA,VAT,HOLY SEE
Honduras,HN,HND,HONDURAS
Hungary,HU,HUN,HUNGARY
Iceland,IS,ISL,ICELAND
India,IN,IND,INDIA
Indonesia,ID,IDN,INDONESIA
Iran (Islamic Republic of),IR,IRN,IRAN (ISLAMIC REPUBLIC OF)
Iraq,IQ,IRQ,IRAQ
Ireland,IE,IRL,IRELAND
Isle of Man,IM,IMN,ISLE OF MAN
Israel,IL,ISR,ISRAEL
Italy,IT,ITA,ITALY
Jamaica,JM,JAM,JAMAICA
Japan,JP,JPN,JAPAN
Jersey,JE,JEY,JERSEY
Jordan,JO,JOR,JORDAN
Kazakhstan,KZ,KAZ,KAZAKHSTAN
Kenya,KE,KEN,KENYA
Kiribati,KI,KIR,KIRIBATI
Kuwait,KW,KWT,KUWAIT
Kyrgyzstan,KG,KGZ,KYRGYZSTAN
Lao People's Democratic Republic,LA,LAO,LAO PEOPLE’S DEMOCRATIC REPUBLIC
Latvia,LV,LVA,LATVIA
Lebanon,LB,LBN,LEBANON
Lesotho,LS,LSO,LESOTHO
Liberia,LR,LBR,LIBERIA
Libya,LY,LBY,LIBYA
Liechtenstein,LI,LIE,LIECHTENSTEIN
Lithuania,LT,LTU,LITHUANIA
Luxembourg,LU,LUX,LUXEMBOURG
Madagascar,MG,MDG,MADAGASCAR
Malawi,MW,MWI,MALAWI
Malaysia,MY,MYS,MALAYSIA
Maldives,MV,MDV,MALDIVES
Mali,ML,MLI,MALI
Malta,MT,MLT,MALTA
Marshall Islands,MH,MHL,MARSHALL ISLANDS
Martinique,MQ,MTQ,MARTINIQUE
Mauritania,MR,MRT,MAURITANIA
Mauritius,MU,MUS,MAURITIUS
Mayotte,YT,MYT,MAYOTTE
Mexico,MX,MEX,MEXICO
Micronesia (Federated States of),FM,FSM,MICRONESIA (FEDERATED STATES OF)
Monaco,MC,MCO,MONACO
Mongolia,MN,MNG,MONGOLIA
Montenegro,ME,MNE,MONTENEGRO
Montserrat,MS,MSR,MONTSERRAT
Morocco,MA,MAR,MOROCCO
Mozambique,MZ,MOZ,MOZAMBIQUE
Myanmar,MM,MMR,MYANMAR
Namibia,NA,NAM,NAMIBIA
Nauru,NR,NRU,NAURU
Nepal,NP,NPL,NEPAL
Netherlands,NL,NLD,NETHERLANDS
New Caledonia,NC,NCL,NEW CALEDONIA
New Zealand,NZ,NZL,NEW ZEALAND
Nicaragua,NI,NIC,NICARAGUA
Niger,NE,NER,NIGER
Nigeria,NG,NGA,NIGERIA
Niue,NU,NIU,NIUE
Norfolk Island,NF,NFK,NORFOLK ISLAND
Northern Mariana Islands,MP,MNP,NORTHERN MARIANA ISLANDS
Norway,NO,NOR,NORWAY
Oman,OM,OMN,OMAN
Pakistan,PK,PAK,PAKISTAN
Palau,PW,PLW,PALAU
Panama,PA,PAN,PANAMA
Papua New Guinea,PG,PNG,PAPUA NEW GUINEA
Paraguay,PY,PRY,PARAGUAY
Peru,PE,PER,PERU
Philippines,PH,PHL,PHILIPPINES
Pitcairn,PN,PCN,PITCAIRN
Poland,PL,POL,POLAND
Portugal,PT,PRT,PORTUGAL
Puerto Rico,PR,PRI,PUERTO RICO
Qatar,QA,QAT,QATAR
Republic of Korea,KR,KOR,KOREA (THE REPUBLIC OF)
Republic of Moldova,MD,MDA,MOLDOVA (THE REPUBLIC OF)
Romania,RO,ROU,ROMANIA
Russian Federation,RU,RUS,RUSSIAN FEDERATION
Rwanda,RW,RWA,RWANDA
Réunion,RE,REU,RÉUNION
Saint Barthélemy,BL,BLM,SAINT BARTHÉLEMY
Saint Helena,SH,SHN,"SAINT HELENA, ASCENSION AND TRISTAN DA CUNHA"
Saint Kitts and Nevis,KN,KNA,SAINT KITTS AND NEVIS
Saint Lucia,LC,LCA,SAINT LUCIA
Saint Martin (French Part),MF,MAF,SAINT MARTIN (FRENCH PART)
Saint Pierre and Miquelon,PM,SPM,SAINT PIERRE AND MIQUELON
Saint Vincent and the Grenadines,VC,VCT,SAINT VINCENT AND THE GRENADINES
Samoa,WS,WSM,SAMOA
San Marino,SM,SMR,SAN MARINO
Sao Tome and Principe,ST,STP,SAO TOME AND PRINCIPE
Sark,,,
Saudi Arabia,SA,SAU,SAUDI ARABIA
Senegal,SN,SEN,SENEGAL
Serbia,RS,SRB,SERBIA
Seychelles,SC,SYC,SEYCHELLES
Sierra Leone,SL,SLE,SIERRA LEONE
Singapore,SG,SGP,SINGAPORE
Sint Maarten (Dutch part),SX,SXM,SINT MAARTEN (DUTCH PART)
Slovakia,SK,SVK,SLOVAKIA
Slovenia,SI,SVN,SLOVENIA
Solomon Islands,SB,SLB,SOLOMON ISLANDS
Somalia,SO,SOM,SOMALIA
South Africa,ZA,ZAF,SOUTH AFRICA
South Georgia and the South Sandwich Islands,GS,SGS,SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS
South Sudan,SS,SSD,SOUTH SUDAN
Spain,ES,ESP,SPAIN
Sri Lanka,LK,LKA,SRI LANKA
State of Palestine,PS,PSE,"PALESTINE, STATE OF"
Sudan,SD,SDN,SUDAN
Suriname,SR,SUR,SURINAME
Svalbard and Jan Mayen Islands,SJ,SJM,SVALBARD AND JAN MAYEN
Swaziland,SZ,SWZ,SWAZILAND
Sweden,SE,SWE,SWEDEN
Switzerland,CH,CHE,SWITZERLAND
Syrian Arab Republic,SY,SYR,SYRIAN ARAB REPUBLIC
Tajikistan,TJ,TJK,TAJIKISTAN
Thailand,TH,THA,THAILAND
The former Yugoslav Republic of Macedonia,MK,MKD,MACEDONIA (THE FORMER YUGOSLAV REPUBLIC OF)
Timor-Leste,TL,TLS,TIMOR-LESTE
Togo,TG,TGO,TOGO
Tokelau,TK,TKL,TOKELAU
Tonga,TO,TON,TONGA
Trinidad and Tobago,TT,TTO,TRINIDAD AND TOBAGO
Tunisia,TN,TUN,TUNISIA
Turkey,TR,TUR,TURKEY
Turkmenistan,TM,TKM,TURKMENISTAN
Turks and Caicos Islands,TC,TCA,TURKS AND CAICOS ISLANDS
Tuvalu,TV,TUV,TUVALU
Uganda,UG,UGA,UGANDA
Ukraine,UA,UKR,UKRAINE
United Arab Emirates,AE,ARE,UNITED ARAB EMIRATES
United Kingdom of Great Britain and Northern Ireland,GB,GBR,UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND
United Republic of Tanzania,TZ,TZA,"TANZANIA, UNITED REPUBLIC OF"
United States Minor Outlying Islands,UM,UMI,UNITED STATES MINOR OUTLYING ISLANDS
United States Virgin Islands,VI,VIR,VIRGIN ISLANDS (U.S.)
United States of America,US,USA,UNITED STATES OF AMERICA
Uruguay,UY,URY,URUGUAY
Uzbekistan,UZ,UZB,UZBEKISTAN
Vanuatu,VU,VUT,VANUATU
Venezuela (Bolivarian Republic of),VE,VEN,VENEZUELA (BOLIVARIAN REPUBLIC OF)
Viet Nam,VN,VNM,VIET NAM
Wallis and Futuna Islands,WF,WLF,WALLIS AND FUTUNA
Western Sahara,EH,ESH,WESTERN SAHARA
Yemen,YE,YEM,YEMEN
Zambia,ZM,ZMB,ZAMBIA
Zimbabwe,ZW,ZWE,ZIMBABWE
Åland Islands,AX,ALA,ÅLAND ISLANDS
"""

country_codes = pe.load_from_memory("csv",  countrycodes.lower()).to_array()
