"""
Cultural knowledge base for West African regions.
Curated historical and cultural data used to ground narrative prompts.
"""

REGIONS = {
    "ghana": {
        "name": "Gold Coast / Ghana",
        "modern_name": "Ghana",
        "colonial_name": "Gold Coast",
        "languages": ["Akan (Twi, Fante)", "Ewe", "Ga", "Dagbani", "Hausa"],
        "ethnic_groups": ["Ashanti", "Fante", "Ewe", "Ga-Adangbe", "Dagomba"],
        "geography": "Coastal plains along the Gulf of Guinea rising to the Ashanti Plateau and northern savanna. Dense tropical forest in the central belt. The Volta River system dominates the east.",
        "decades": {
            "1900s": {
                "events": [
                    "British consolidation of Gold Coast Colony",
                    "Ashanti War of the Golden Stool (1900)",
                    "Expansion of cocoa farming in the forest belt",
                ],
                "daily_life": "Most families engaged in farming (cocoa, palm oil, yams), fishing along the coast, or trading at regional markets. Extended family compounds were the center of social life.",
                "cultural_practices": "Akan naming ceremonies (outdooring on the 8th day), Adinkra cloth weaving, gold weight trading systems, oral history maintained by court historians.",
            },
            "1910s": {
                "events": [
                    "Gold Coast becomes world's largest cocoa producer",
                    "Development of railways connecting Accra to Kumasi",
                    "World War I — Gold Coast soldiers serve in East Africa campaign",
                ],
                "daily_life": "Growing cocoa economy transforms rural life. Market women gain economic independence through trading networks. Mission schools expand Western education alongside traditional apprenticeships.",
                "cultural_practices": "Kente cloth weaving reaches artistic heights in Bonwire. Highlife music begins evolving from brass band traditions. Storytelling and Anansesem (spider stories) remain the primary evening entertainment.",
            },
            "1920s": {
                "events": [
                    "Cocoa hold-ups — farmers resist European price fixing",
                    "Emergence of early nationalist newspapers",
                    "Expansion of Achimota School as center of African education",
                ],
                "daily_life": "Urban centers like Accra and Kumasi grow rapidly. Dual economy emerges — traditional farming alongside cash crop production. Women dominate local and regional trade networks.",
                "cultural_practices": "Highlife music scene flourishes in coastal towns. Traditional festivals like Homowo (Ga) and Odwira (Ashanti) maintain cultural continuity. Secret societies and age-grade systems organize community labor.",
            },
            "1930s": {
                "events": [
                    "Great Depression devastates cocoa prices",
                    "Cocoa swollen shoot disease threatens livelihoods",
                    "Youth movements begin organizing for political representation",
                ],
                "daily_life": "Economic hardship strengthens communal support systems. Extended families pool resources. Many young men migrate to coastal cities for work in ports and mines.",
                "cultural_practices": "Palm wine bars become centers of social life and music. Adinkra symbolism carries philosophical meanings — Sankofa, Gye Nyame, Dwennimmen. Funeral celebrations are elaborate multi-day affairs demonstrating family status.",
            },
            "1940s": {
                "events": [
                    "World War II — Gold Coast soldiers serve in Burma campaign",
                    "1948 Accra riots after ex-servicemen protest",
                    "Kwame Nkrumah returns from abroad",
                    "United Gold Coast Convention formed",
                ],
                "daily_life": "Post-war ferment. Returning soldiers bring new ideas about freedom and self-governance. Market women's networks serve as informal communication systems. Radio broadcasts begin reaching urban areas.",
                "cultural_practices": "Concert party theater combines traditional storytelling with modern themes. Highlife bands like E.T. Mensah and the Tempos define a golden age. Kente cloth gains symbolic importance in emerging nationalist movement.",
            },
            "1950s": {
                "events": [
                    "Convention People's Party founded by Nkrumah (1949)",
                    "Positive Action campaign and Nkrumah's imprisonment",
                    "Ghana becomes first sub-Saharan African nation to gain independence (March 6, 1957)",
                    "'Freedom and Justice' declared as national motto",
                ],
                "daily_life": "Independence fervor transforms daily conversation. Schools expand rapidly. New national symbols and institutions being created. The Black Star becomes a symbol of pan-African hope.",
                "cultural_practices": "Independence celebrations blend traditional drumming with modern brass bands. Kente cloth worn at state occasions becomes a global symbol. Highlife music carries messages of freedom and unity.",
            },
        },
        "occupations": ["Cocoa farming", "Gold mining", "Fishing", "Market trading", "Kente weaving", "Goldsmithing", "Teaching", "Blacksmithing", "Palm wine tapping"],
        "trade_patterns": "Complex trading networks radiating from coastal ports (Accra, Cape Coast, Takoradi) through forest belt markets to northern savanna trade routes connecting to the Sahel. Women dominated local and regional trade; men dominated long-distance caravan trade.",
        "diaspora_connections": "Enslaved Africans from the Gold Coast were transported primarily to the Caribbean (Jamaica, Barbados) and the American South. The Door of No Return at Cape Coast Castle is a pilgrimage site. Akan cultural survivals include naming practices, ring shout traditions, and Gullah Geechee culture in the American Southeast.",
        "migration_patterns": "Internal migration from northern regions to southern cocoa belt. Post-independence migration to UK and North America for education. Significant Ghanaian communities in London, New York, Toronto, and Houston.",
    },
    "nigeria": {
        "name": "Yorubaland / Nigeria",
        "modern_name": "Nigeria",
        "colonial_name": "British Nigeria (Colony and Protectorate)",
        "languages": ["Yoruba", "Igbo", "Hausa", "Edo", "Ijaw", "Efik"],
        "ethnic_groups": ["Yoruba", "Igbo", "Hausa-Fulani", "Edo (Benin)", "Ijaw"],
        "geography": "From the mangrove swamps of the Niger Delta, through dense tropical rainforest in the south, to open savanna in the north. The Niger and Benue rivers converge at Lokoja. Lagos sits on a lagoon system.",
        "decades": {
            "1900s": {
                "events": [
                    "British conquest of Benin Kingdom (1897 aftermath)",
                    "Consolidation of Northern and Southern Protectorates",
                    "Aro Expedition in Igboland",
                ],
                "daily_life": "Yoruba cities like Ibadan and Abeokuta are among Africa's largest urban centers. Compound living with extended families. Markets operate on four-day cycles (ojo ale). Farming, weaving, and ironwork sustain communities.",
                "cultural_practices": "Yoruba religion (Ifa divination, Orisha worship) deeply woven into daily life. Masquerade festivals (Egungun, Gelede) mark seasonal transitions. Elaborate beadwork and indigo dyeing (adire) are women's arts.",
            },
            "1920s": {
                "events": [
                    "Herbert Macaulay leads early nationalist agitation in Lagos",
                    "Aba Women's War (1929) — Igbo women's mass protest against colonial taxation",
                    "Growth of Lagos as commercial and cultural center",
                ],
                "daily_life": "Lagos emerges as a cosmopolitan center mixing Yoruba, Igbo, Hausa, Sierra Leonean Creole, and Brazilian returnee cultures. Juju music and Apala develop in Yoruba communities. Islam and Christianity spread alongside traditional religion.",
                "cultural_practices": "Naming ceremonies (isomoloruko) on the eighth day. Yoruba apprenticeship system trains young people in trades. Aso oke cloth weaving for special occasions. Talking drums (dundun) carry messages between towns.",
            },
            "1940s": {
                "events": [
                    "Nigerian soldiers serve in Burma and East Africa during WWII",
                    "General strike of 1945",
                    "Richards Constitution introduces regional governance",
                    "Nnamdi Azikiwe's newspaper 'West African Pilot' galvanizes nationalism",
                ],
                "daily_life": "Post-war political awakening. Trade unions organize workers. Night schools expand literacy. Highlife and juju music played at social gatherings. Women traders control vast informal economic networks.",
                "cultural_practices": "Owambe party culture — elaborate celebrations for naming, weddings, funerals with matching family cloth (aso ebi). Storytelling sessions with Tortoise tales. Pottery, calabash carving, and bronze casting continue ancient traditions.",
            },
            "1950s": {
                "events": [
                    "Nigeria moves toward independence with regional self-governance",
                    "Independence achieved October 1, 1960",
                    "Lagos grows to over a million people",
                    "Chinua Achebe publishes 'Things Fall Apart' (1958)",
                ],
                "daily_life": "Rapid urbanization. University of Ibadan becomes intellectual center. Civil service expands. Young Nigerians study abroad in the UK and US. Return to build the new nation.",
                "cultural_practices": "Wole Soyinka and the Mbari Club launch a literary renaissance. Bobby Benson's band defines Lagos nightlife. Traditional wrestling, horse racing (durbar), and festivals continue alongside modern entertainment.",
            },
        },
        "occupations": ["Farming (yam, cassava, palm oil)", "Trading (market women)", "Weaving (aso oke, adire)", "Blacksmithing", "Fishing", "Bronze casting", "Teaching", "Clergy", "Palm wine tapping"],
        "trade_patterns": "Trans-Saharan trade routes from northern Nigeria connecting to North Africa. Coastal trade through Lagos and Calabar. Internal networks along rivers and forest paths. Yoruba market women operated credit systems (esusu/ajo).",
        "diaspora_connections": "Yoruba culture is one of the most widely dispersed African traditions in the Americas. Enslaved Yoruba people carried Orisha worship to Cuba (Santería/Lucumí), Brazil (Candomblé), Haiti (Vodou), and Trinidad. Yoruba language elements survive in Gullah, Cuban Spanish, and Brazilian Portuguese. The 'Aguda' community — freed slaves who returned to Lagos from Brazil — brought back Afro-Brazilian architectural and culinary traditions.",
        "migration_patterns": "Post-independence migration to UK for education, later to US. Oil boom era (1970s) drew migrants from across West Africa. Significant Nigerian communities in London, Houston, Atlanta, and the DC metro area.",
    },
    "senegambia": {
        "name": "Senegambia",
        "modern_name": "Senegal and The Gambia",
        "colonial_name": "French West Africa (Senegal) / British Gambia",
        "languages": ["Wolof", "Mandinka", "Pulaar (Fula)", "Serer", "Jola", "French"],
        "ethnic_groups": ["Wolof", "Mandinka", "Fula (Fulani)", "Serer", "Jola"],
        "geography": "Semi-arid Sahel in the north transitioning to savanna woodlands. The Gambia River cuts through the heart of the region. Senegal's Cap-Vert peninsula juts into the Atlantic. Casamance in the south has lush tropical forest.",
        "decades": {
            "1940s": {
                "events": [
                    "Senegalese tirailleurs serve in Free French forces during WWII",
                    "Thiaroye massacre (1944) — colonial troops shot protesting soldiers",
                    "Léopold Sédar Senghor begins political career",
                    "Négritude movement flourishes in Dakar",
                ],
                "daily_life": "Groundnut (peanut) farming dominates rural economy. Griot families maintain centuries of oral history. Extended family compounds (concessions) organized around a central courtyard. Dakar's Medina neighborhood pulses with life.",
                "cultural_practices": "Griot tradition (jali) — hereditary musicians and historians who carry the memory of lineages. Sabar drumming and dance at celebrations. Teranga (hospitality) is a core cultural value. Three rounds of attaya (tea ceremony) structure social visits.",
            },
            "1950s": {
                "events": [
                    "Senghor and Négritude shape pan-African intellectual thought",
                    "Senegal gains independence in 1960",
                    "Dakar becomes cultural capital of Francophone Africa",
                ],
                "daily_life": "Wolof urban culture mixes with French colonial influence. Elegant dress (boubou and matching headwrap) is a point of pride. Market gardens supply Dakar's growing population. Fishing pirogues launch daily from the coast.",
                "cultural_practices": "Mbalax music emerges from sabar drum traditions. Elaborate naming ceremonies (ngénte). Sufi Muslim brotherhoods (Mouride, Tijaniyya) organize economic and spiritual life. Wrestlers (laamb) are national heroes.",
            },
        },
        "occupations": ["Groundnut farming", "Fishing", "Griot (musician/historian)", "Weaving", "Blacksmithing", "Goldsmithing", "Trading", "Herding (Fula)"],
        "trade_patterns": "Trans-Saharan gold and salt trade. Groundnut export through Dakar and Banjul. River trade along the Gambia. Dakar served as a major port for French West Africa.",
        "diaspora_connections": "Gorée Island off Dakar is a UNESCO World Heritage Site and slavery memorial. Mandinka and Wolof people were among those enslaved and transported to the Americas. Mandinka cultural traces in the Gullah Geechee communities. Alex Haley's 'Roots' traced his ancestry to Juffureh in The Gambia.",
        "migration_patterns": "Migration to France, particularly Paris, from the colonial era onward. Mouride traders established networks across Europe and North America. Gambian communities in the UK.",
    },
    "dahomey": {
        "name": "Dahomey / Benin Republic",
        "modern_name": "Benin (Republic of)",
        "colonial_name": "French Dahomey",
        "languages": ["Fon", "Yoruba", "Bariba", "Dendi", "French"],
        "ethnic_groups": ["Fon", "Yoruba", "Bariba", "Somba", "Adja"],
        "geography": "Narrow coastal strip with lagoons and coconut palms. Terre de barre clay plateau inland. Northern savanna. The Ouémé River valley is fertile agricultural land.",
        "decades": {
            "1940s": {
                "events": [
                    "Dahomey under Vichy, then Free French control during WWII",
                    "Porto-Novo and Cotonou grow as urban centers",
                    "Rise of educated elite seeking political participation",
                ],
                "daily_life": "Palm oil production dominates the economy. Elaborate markets operated primarily by women. Compound living with patrilineal family structures. Vodun (Voodoo) practices deeply integrated into daily rhythms — offerings, divination, and seasonal festivals.",
                "cultural_practices": "The legacy of the Dahomey Amazons (Agojie) — elite female warriors — lives in collective memory. Appliqué cloth banners depicting royal history. Zangbeto night watchmen patrol villages. Gelede masquerade honors mothers and powerful women.",
            },
        },
        "occupations": ["Palm oil production", "Farming", "Trading", "Weaving", "Pottery", "Ironwork", "Vodun priest/priestess", "Fishing"],
        "trade_patterns": "Ouidah was a major slave trading port. Post-abolition, palm oil became the primary export. Trade routes connected the coast to the Yoruba hinterland and northward.",
        "diaspora_connections": "Ouidah was one of the largest slave embarkation points in West Africa. Fon and Ewe religious practices survived as Haitian Vodou, Brazilian Candomblé, and Louisiana Voodoo. The 'Aguda' — Afro-Brazilians who returned to Dahomey — brought back Catholic-syncretic traditions. The annual Vodun festival in Ouidah draws diaspora visitors.",
        "migration_patterns": "Migration to France and other Francophone countries. Growing diaspora in the United States, particularly in New York and the DMV area.",
    },
    "sierra_leone": {
        "name": "Sierra Leone",
        "modern_name": "Sierra Leone",
        "colonial_name": "British Sierra Leone",
        "languages": ["Krio", "Temne", "Mende", "Limba", "Kono"],
        "ethnic_groups": ["Temne", "Mende", "Krio (Creole)", "Limba", "Kono"],
        "geography": "From white sand beaches and mangrove swamps along the coast, through tropical rainforest, to the Guinea Highlands in the east. Freetown sits on a mountainous peninsula — the 'Lion Mountains' that gave the country its name.",
        "decades": {
            "1940s": {
                "events": [
                    "Freetown serves as a major Allied naval base during WWII",
                    "1945 general strike",
                    "Constitutional reforms begin",
                    "Sierra Leone Selection Trust controls diamond mining",
                ],
                "daily_life": "Freetown's Krio community blends African, European, and Caribbean cultural elements — a unique Creole culture. Upcountry, farming and diamond mining shape livelihoods. Secret societies (Poro for men, Sande/Bundu for women) govern social transitions.",
                "cultural_practices": "Krio culture features distinctive wooden architecture with wrap-around verandas, elaborate funeral customs (awujoh), and a cuisine blending African and English traditions. Storytelling traditions feature Anansi the spider. Masquerade societies perform at festivals.",
            },
        },
        "occupations": ["Diamond mining", "Farming (rice, cassava)", "Fishing", "Trading", "Teaching", "Tailoring", "Government service (Krio elite)"],
        "trade_patterns": "Diamond exports dominate the economy. Rice farming for subsistence. Freetown as a port connecting West African interior to Atlantic trade. Kola nut trade with northern neighbors.",
        "diaspora_connections": "Freetown was founded by freed slaves from Britain, Nova Scotia, Jamaica (Maroons), and recaptured Africans. Krio culture is itself a diaspora creation. Sierra Leonean communities in the UK, particularly London and the Midlands. Gullah Geechee connections — some scholars trace direct links to Sierra Leone's rice-growing cultures.",
        "migration_patterns": "Migration to UK during colonial era for education. Civil war (1991-2002) created large refugee communities in the US (particularly the DC area and Philadelphia), UK, and neighboring West African countries.",
    },
}

GENERAL_WEST_AFRICA = {
    "colonial_context": "European colonization of West Africa intensified from the mid-19th century. The Scramble for Africa (1884-1885 Berlin Conference) formalized colonial boundaries that often divided ethnic groups. British colonies (Gold Coast, Nigeria, Sierra Leone, Gambia) and French colonies (Senegal, Dahomey, Guinea, Ivory Coast) imposed different administrative systems but similarly disrupted traditional governance, land tenure, and trade patterns.",
    "independence_wave": "Beginning with Ghana in 1957, West African nations achieved independence through the early 1960s. This period was marked by immense optimism, pan-African solidarity, and ambitious nation-building projects.",
    "shared_cultural_elements": [
        "Oral tradition and griot/storytelling cultures",
        "Extended family compound living",
        "Age-grade social organization",
        "Elaborate funeral and naming ceremonies",
        "Market women's economic networks",
        "Apprenticeship-based skill transmission",
        "Polyrhythmic drumming traditions",
        "Masquerade and festival cycles",
        "Respect for elders and ancestor veneration",
        "Communal labor practices (nnoboa, etc.)",
    ],
    "transatlantic_slavery": "Between the 16th and 19th centuries, an estimated 12.5 million Africans were forcibly transported across the Atlantic. West Africa — from Senegambia to Angola — was the primary source region. Major embarkation points included Gorée Island (Senegal), Cape Coast Castle (Ghana), Badagry and Lagos (Nigeria), and Ouidah (Dahomey/Benin). The trauma of this forced migration is central to understanding the African diaspora experience.",
}


def get_region_data(region_query: str) -> dict | None:
    """Find the best matching region for a user's query."""
    query = region_query.lower()

    direct_matches = {
        "ghana": "ghana",
        "gold coast": "ghana",
        "ashanti": "ghana",
        "akan": "ghana",
        "nigeria": "nigeria",
        "yoruba": "nigeria",
        "igbo": "nigeria",
        "yorubaland": "nigeria",
        "senegal": "senegambia",
        "gambia": "senegambia",
        "senegambia": "senegambia",
        "wolof": "senegambia",
        "mandinka": "senegambia",
        "dahomey": "dahomey",
        "benin": "dahomey",
        "fon": "dahomey",
        "sierra leone": "sierra_leone",
        "freetown": "sierra_leone",
        "krio": "sierra_leone",
    }

    for keyword, region_key in direct_matches.items():
        if keyword in query:
            return REGIONS[region_key]

    if "west africa" in query or "west african" in query:
        return REGIONS["ghana"]

    return None


def get_decade_data(region_data: dict, time_query: str) -> dict | None:
    """Find the best matching decade for a time period query."""
    query = time_query.lower()
    decades = region_data.get("decades", {})

    for decade_key in decades:
        if decade_key[:3] in query:
            return decades[decade_key]

    decade_keywords = {
        "1900": "1900s", "1910": "1910s", "1920": "1920s", "1930": "1930s",
        "1940": "1940s", "1950": "1950s",
    }
    for year, decade in decade_keywords.items():
        if year in query and decade in decades:
            return decades[decade]

    generation_mappings = {
        "great-grandmother": "1920s",
        "great grandmother": "1920s",
        "grandmother": "1940s",
        "grandma": "1940s",
        "grandfather": "1940s",
        "grandpa": "1940s",
        "parent": "1950s",
        "mother": "1950s",
        "father": "1950s",
        "pre-independence": "1950s",
        "independence": "1950s",
        "colonial": "1920s",
        "world war": "1940s",
        "wwii": "1940s",
        "ww2": "1940s",
    }
    for keyword, decade in generation_mappings.items():
        if keyword in query and decade in decades:
            return decades[decade]

    available = list(decades.keys())
    if available:
        return decades[available[-1]]

    return None
