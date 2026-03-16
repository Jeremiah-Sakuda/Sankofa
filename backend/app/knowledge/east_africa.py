"""
Cultural knowledge base for East African regions.
Curated historical and cultural data used to ground narrative prompts.
"""

REGIONS = {
    "kenya": {
        "name": "Kenya",
        "modern_name": "Kenya",
        "colonial_name": "British East Africa / Kenya Colony",
        "languages": ["Swahili", "Kikuyu", "Dholuo", "Kamba", "Kalenjin", "Maasai (Maa)", "English"],
        "ethnic_groups": ["Kikuyu", "Luo", "Maasai", "Kamba", "Kalenjin", "Luhya", "Swahili (coastal)"],
        "geography": "From the white coral beaches and mangrove creeks of the Indian Ocean coast, through the dry Nyika scrubland, up to the fertile Central Highlands around Mount Kenya. The Great Rift Valley slices north-south, studded with soda lakes. Western Kenya rolls into the shores of Lake Victoria. Nairobi sits at 1,700m on a high plateau.",
        "decades": {
            "1900s": {
                "events": [
                    "British East Africa Protectorate consolidates colonial control",
                    "Uganda Railway reaches Lake Victoria (completed 1901) — 'Lunatic Express'",
                    "Large-scale alienation of Kikuyu and Maasai lands for white settler farms in the 'White Highlands'",
                ],
                "daily_life": "Kikuyu families farm millet, sweet potatoes, and beans on shamba plots in the Central Highlands. Maasai pastoralists move cattle across the Rift Valley following seasonal grazing. Swahili traders in Mombasa operate within centuries-old Indian Ocean commerce. The railway brings Indian laborers whose descendants form a permanent community.",
                "cultural_practices": "Kikuyu age-set initiation (irua) marks the transition to adulthood. Maasai warriors (moran) undergo elaborate ceremonies — the eunoto graduation from junior to senior warrior. Swahili coastal culture blends African, Arab, and Persian traditions in architecture (coral stone houses), cuisine (pilau, biryani), and the taarab music tradition.",
            },
            "1910s": {
                "events": [
                    "World War I — East Africa campaign, Africans conscripted as soldiers and porters (Carrier Corps)",
                    "Tens of thousands of Kenyan porters die from disease and exhaustion",
                    "Settler farms expand, pushing more communities off ancestral lands",
                ],
                "daily_life": "The war devastates rural communities — young men taken as carriers, crops and livestock requisitioned. Women take on expanded agricultural roles. Returning survivors bring new perspectives on colonial power. Settler coffee and tea plantations use African labor under the kipande pass system.",
                "cultural_practices": "Luo fishing communities on Lake Victoria maintain nyatiti lyre traditions. Kikuyu storytelling sessions around the hearth feature tales of Wanjiru and the ogre. Maasai age-set ceremonies continue despite colonial disruption. Swahili poets compose in the centuries-old utenzi verse form.",
            },
            "1920s": {
                "events": [
                    "Kenya declared a Crown Colony (1920)",
                    "Harry Thuku arrested for anti-colonial organizing (1922) — mass protests",
                    "Kikuyu Central Association formed, advocating for land rights",
                    "Forced labor and the kipande (identity pass) system tighten colonial control",
                ],
                "daily_life": "The kipande system requires African men to carry an identity document at all times — humiliating searches are routine. Squatter labor on settler farms grows. Mission schools offer education but demand cultural assimilation. Urban Nairobi develops an African quarter but under strict segregation.",
                "cultural_practices": "Controversy over Kikuyu female initiation practices becomes a political flashpoint — missionaries demand abolition, the Kikuyu defend cultural sovereignty. Independent schools movement begins. Beadwork and body decoration mark Maasai social status and age-set membership.",
            },
            "1930s": {
                "events": [
                    "Great Depression hits Kenya — crop prices collapse",
                    "Jomo Kenyatta travels to London to advocate for Kikuyu land rights",
                    "Growing tensions between settlers, colonial government, and African communities",
                ],
                "daily_life": "Economic hardship drives more Africans into wage labor on settler farms and in Nairobi. The 'squatter' system deepens — families live on European farms in exchange for labor. Tea and coffee picking become major occupations for women. Markets in towns like Nyeri, Kisumu, and Mombasa bustle with trade.",
                "cultural_practices": "Kenyatta publishes 'Facing Mount Kenya' (1938) — an ethnography defending Kikuyu culture. Gospel music blends with traditional harmonies in mission churches. Luo benga guitar style begins to emerge. Coastal Swahili weddings feature elaborate henna, taarab music, and multi-day celebrations.",
            },
            "1940s": {
                "events": [
                    "World War II — over 75,000 Kenyans serve in Burma, Ethiopia, and Madagascar",
                    "Returning soldiers radicalized by wartime experiences",
                    "Kenya African Union (KAU) founded, Kenyatta becomes president",
                    "Land hunger intensifies — 'White Highlands' controversy boils over",
                ],
                "daily_life": "Post-war unrest grips the colony. African ex-soldiers demand equality. Nairobi's African neighborhoods — Eastlands, Pumwani — grow rapidly. Women's self-help groups (harambee spirit) emerge. Tea picking, domestic service, and dock work in Mombasa employ thousands.",
                "cultural_practices": "Harambee (pulling together) ethos organizes community self-help. Nyatiti lyre and ohangla drumming at Luo social gatherings. Kikuyu women's mwomboko dance. Urban Nairobi develops a cosmopolitan nightlife mixing African, Indian, and European influences.",
            },
            "1950s": {
                "events": [
                    "Mau Mau uprising (1952–1960) — armed resistance against colonial rule and land theft",
                    "State of Emergency declared — mass detention, villagization, brutal repression",
                    "Jomo Kenyatta imprisoned (1953)",
                    "Lancaster House conferences begin path to independence (achieved 1963)",
                ],
                "daily_life": "The Emergency transforms daily life — Kikuyu communities forcibly relocated into guarded villages. Screening, detention camps, and curfews. Despite repression, spirit of resistance strengthens. In non-Kikuyu areas and cities, life continues with growing political consciousness across ethnic lines.",
                "cultural_practices": "Mau Mau oath-taking ceremonies draw on traditional spiritual practices. Songs of resistance circulate in detention camps. The struggle creates shared martyrology and national consciousness. Benga music and Swahili rumba emerge in Nairobi's clubs. Independence celebrations will blend all Kenya's cultures.",
            },
        },
        "occupations": ["Farming (coffee, tea, maize, beans)", "Pastoralism (cattle, goats)", "Fishing (Lake Victoria)", "Dock work (Mombasa)", "Domestic service", "Market trading", "Teaching", "Railway work", "Carpentry"],
        "trade_patterns": "Mombasa as the gateway port for East Africa, connecting to the Indian Ocean trade network reaching India, Arabia, and Persia. The Uganda Railway linked the coast to the interior. Regional markets (open-air) at crossroads and towns. Maasai cattle trade across the Rift Valley. Indian merchants operated as middlemen (duka-wallahs) throughout the colony.",
        "diaspora_connections": "Kenyan runners have become global icons. Significant Kenyan communities in the UK (London), US (particularly the DMV area, Texas, Minnesota), and the Gulf states. Swahili language has become a pan-African symbol studied worldwide. Maasai culture is one of the most recognized African cultures globally. Barack Obama's Kenyan heritage brought global attention to Luo culture.",
        "migration_patterns": "Colonial-era labor migration from rural areas to Nairobi and Mombasa. Post-independence migration to the UK and US for education. Professional migration to the Gulf states, South Africa, and Australia. Internal rural-to-urban migration continues to transform Nairobi and other cities.",
    },
    "tanzania": {
        "name": "Tanganyika / Tanzania",
        "modern_name": "Tanzania",
        "colonial_name": "German East Africa (to 1919) / Tanganyika Territory (British Mandate)",
        "languages": ["Swahili", "Sukuma", "Chagga", "Haya", "Nyamwezi", "Maasai (Maa)", "Arabic (Zanzibar)", "English"],
        "ethnic_groups": ["Sukuma", "Chagga", "Nyamwezi", "Haya", "Maasai", "Swahili-Shirazi (Zanzibar)", "Hadza"],
        "geography": "From the spice island of Zanzibar and the palm-fringed coast, across vast central plateau savanna, to the volcanic highlands of Kilimanjaro and Ngorongoro. Lake Victoria borders the northwest, Lake Tanganyika the west. The Serengeti plains stretch endlessly under enormous skies. Dar es Salaam sits on a natural harbor.",
        "decades": {
            "1900s": {
                "events": [
                    "German colonial rule consolidates across German East Africa",
                    "Maji Maji Rebellion (1905–1907) — massive uprising against forced cotton cultivation, brutally suppressed",
                    "Tens of thousands die in the rebellion and subsequent famine",
                ],
                "daily_life": "Sukuma and Nyamwezi farmers cultivate millet and sorghum on the central plateau. Chagga communities farm coffee and bananas on the slopes of Kilimanjaro. Zanzibar's clove plantations use formerly enslaved labor. German forced-labor policies and the hut tax disrupt traditional livelihoods. Caravan trade routes still operate through Nyamwezi country.",
                "cultural_practices": "Sukuma snake dance (bugobogobo) and harvest festivals. Chagga banana beer brewing and elaborate irrigation channels (mfongo) on Kilimanjaro's slopes. Zanzibar's Stone Town — a labyrinth of carved wooden doors, spice markets, and coral-stone architecture. Nyamwezi long-distance trading culture maintains its prestige.",
            },
            "1910s": {
                "events": [
                    "World War I — East African campaign devastates the territory",
                    "German forces under von Lettow-Vorbeck wage guerrilla war across the region",
                    "Massive civilian casualties and displacement",
                    "Treaty of Versailles transfers territory to Britain as League of Nations mandate (1919)",
                ],
                "daily_life": "The war ravages the land — crops destroyed, cattle seized, villages burned. African soldiers (askari) and porters serve on both sides. Famine follows the fighting. The transition from German to British rule brings uncertainty but also the end of some of the harshest German policies.",
                "cultural_practices": "Despite wartime devastation, Swahili poetry (shairi) continues as a literary tradition. Ngoma drumming and dance mark what celebrations remain possible. Zanzibar's taarab music scene persists in the stone courtyards of the old town. Oral histories record the horrors of the war for future generations.",
            },
            "1920s": {
                "events": [
                    "British Mandate administration establishes indirect rule",
                    "Coffee cooperatives form among Chagga farmers — early African economic organization",
                    "Zanzibar clove economy enriches Arab and Indian merchant classes",
                ],
                "daily_life": "British indirect rule works through appointed chiefs — less harsh than German direct rule but still exploitative. Chagga coffee farmers on Kilimanjaro become relatively prosperous. Sisal plantations expand using migrant labor. Dar es Salaam grows as the colonial capital. Zanzibar operates as a separate protectorate with its own Sultan.",
                "cultural_practices": "Chagga initiation ceremonies and clan gatherings maintain social cohesion. Haya communities around Lake Victoria practice banana cultivation and ironworking. Maasai age-set ceremonies continue across the northern borderlands. Zanzibar's multicultural festivals blend Swahili, Arab, Indian, and Comorian traditions.",
            },
            "1930s": {
                "events": [
                    "Great Depression reduces export crop prices",
                    "Chagga Coffee Cooperative strengthens — model for African self-organization",
                    "Growing African educational aspirations, mission schools expand",
                ],
                "daily_life": "Economic hardship strengthens communal bonds. The cooperative movement gives African farmers a collective voice. Young Africans educated at mission schools (like Tabora Government School) begin imagining self-governance. Women's roles in farming and trade remain central to community survival.",
                "cultural_practices": "Storytelling traditions preserve history across all communities. Sukuma dance competitions (bugobogobo and wigashe) draw thousands. Makonde wood carving tradition on the southern coast produces striking sculptures. Swahili literature flourishes — newspapers and poetry in the Roman script.",
            },
            "1940s": {
                "events": [
                    "World War II — Tanganyikan soldiers serve in Burma and the Middle East",
                    "Post-war political awakening across the territory",
                    "Julius Nyerere begins teaching career and political organizing",
                    "Groundnut Scheme failure embarrasses British colonial administration",
                ],
                "daily_life": "Returning soldiers bring new ideas about equality and self-rule. Cooperative movements strengthen. Sisal workers organize for better conditions. Dar es Salaam's Kariakoo market becomes a hub of commerce and conversation. Radio broadcasts in Swahili connect far-flung communities.",
                "cultural_practices": "Swahili becomes a unifying language — spoken across ethnic boundaries. Beni ngoma (brass-band-influenced dance societies) blend African and European musical elements. Zanzibar's music scene produces unique fusions — taarab orchestras with Indian harmonium, Egyptian oud, and African percussion. Coffee ceremonies in Chagga homes cement friendships.",
            },
            "1950s": {
                "events": [
                    "Tanganyika African National Union (TANU) founded by Julius Nyerere (1954)",
                    "TANU wins overwhelming electoral victories",
                    "Nyerere's philosophy of African socialism (Ujamaa) takes shape",
                    "Tanganyika gains independence peacefully (December 9, 1961)",
                    "Zanzibar Revolution (1964) leads to union with Tanganyika, forming Tanzania",
                ],
                "daily_life": "TANU organizes across ethnic lines, unifying the territory through Swahili. Independence fever builds — green, gold, and black everywhere. Nyerere's vision of ujamaa (familyhood) and self-reliance resonates. Schools expand rapidly. The peaceful transition to independence becomes a model for the continent.",
                "cultural_practices": "TANU rallies feature ngoma dancing, freedom songs, and Nyerere's passionate oratory. Swahili poetry celebrates the coming of uhuru (freedom). Makonde sculpture gains international recognition. Zanzibar's music fuses into what will become the taarab-pop hybrid. National culture policy emphasizes unity across 120+ ethnic groups.",
            },
        },
        "occupations": ["Farming (coffee, sisal, cloves, bananas, millet)", "Pastoralism", "Fishing (Lake Victoria, Indian Ocean, Zanzibar)", "Caravan trading", "Clove picking (Zanzibar)", "Dock work (Dar es Salaam)", "Mining", "Wood carving"],
        "trade_patterns": "Zanzibar was the center of the East African trade network — spices, ivory, and enslaved people flowed through its markets for centuries. Dar es Salaam and Tanga as mainland ports. Nyamwezi long-distance caravan routes connected the coast to the Great Lakes interior. Chagga coffee trade through Moshi. Indian Ocean dhow trade connecting to Arabia, India, and Persia.",
        "diaspora_connections": "Zanzibar's history as a trade hub created deep connections to Oman, India, and Persia — Zanzibari communities exist across the Arabian Gulf. Freddie Mercury (born Farrokh Bulsara) is Zanzibar's most famous son. Swahili language and culture are pan-African touchstones. The East African slave trade created diaspora communities across the Indian Ocean world — in Oman, the Persian Gulf, and the Indian subcontinent.",
        "migration_patterns": "Historical caravan routes facilitated internal migration. Indian Ocean trade brought Arab, Indian, and Persian settlers to the coast. Post-independence migration to the UK for education. Zanzibari diaspora in Oman and the Gulf states. Internal villagization under ujamaa policy relocated millions in the 1960s–70s.",
    },
    "ethiopia": {
        "name": "Ethiopia / Abyssinia",
        "modern_name": "Ethiopia",
        "colonial_name": "Abyssinia (never fully colonized — Italian occupation 1936–1941)",
        "languages": ["Amharic", "Oromo (Afaan Oromoo)", "Tigrinya", "Somali", "Sidamo", "Ge'ez (liturgical)"],
        "ethnic_groups": ["Amhara", "Oromo", "Tigray", "Somali", "Sidama", "Gurage", "Wolayta"],
        "geography": "The Ethiopian Highlands — a massive mountain fortress rising above the Horn of Africa, bisected by the Great Rift Valley. Deep river gorges (the Blue Nile canyon), high plateaus (over 2,400m), and the Simien Mountains. The Danakil Depression in the northeast is one of the hottest places on Earth. Lake Tana, source of the Blue Nile, sits in the northwest.",
        "decades": {
            "1900s": {
                "events": [
                    "Emperor Menelik II consolidates the modern Ethiopian state",
                    "Victory at the Battle of Adwa (1896) still resonates — Ethiopia defeats Italian invasion",
                    "Addis Ababa established as the capital (founded 1886, growing rapidly)",
                    "Ethiopia remains independent while the rest of Africa is colonized",
                ],
                "daily_life": "Highland farming families cultivate teff (the grain of injera), barley, wheat, and coffee. Oromo pastoralists herd cattle across the southern and eastern lowlands. The Orthodox Christian calendar structures daily life — fasting days (over 200 per year), saints' days, and dawn church services. Coffee is more than a drink — the ceremony is the heart of social life.",
                "cultural_practices": "Ethiopian Orthodox Christianity, dating to the 4th century, shapes architecture (rock-hewn churches of Lalibela), art (illuminated manuscripts, icon painting), and music (the liturgical chant tradition using the ancient Ge'ez language). The coffee ceremony — roasting, grinding, and brewing in three rounds — is sacred hospitality. Meskel (Finding of the True Cross) festival features enormous bonfires.",
            },
            "1910s": {
                "events": [
                    "Lij Iyasu's brief, controversial reign and deposition",
                    "Empress Zewditu crowned with Ras Tafari as regent and heir (1916)",
                    "Ethiopia remains one of only two independent African nations (with Liberia)",
                ],
                "daily_life": "Rural life continues much as it has for centuries — oxen plowing highland fields, women carrying water from streams, children herding livestock. Addis Ababa modernizes slowly — telephone lines, a few automobiles, the beginning of a government bureaucracy. Trade caravans still carry salt bars (amolé) from the Danakil as currency.",
                "cultural_practices": "The Ethiopian church's intricate liturgical calendar governs eating, fasting, and celebration. Azmari musicians (wandering bards) perform satirical poetry set to music with the masinko (one-stringed fiddle). Elaborate traditional weaving produces the shamma and netela (white cotton garments with decorative borders). Genna (Ethiopian Christmas) features the ancient horseback sport of the same name.",
            },
            "1920s": {
                "events": [
                    "Ras Tafari (future Haile Selassie) modernizes the state",
                    "Ethiopia joins the League of Nations (1923) — first African member",
                    "Abolition of slavery officially proclaimed (though enforcement is gradual)",
                    "First Ethiopian students sent abroad for education",
                ],
                "daily_life": "Ras Tafari's modernization brings new schools, hospitals, and printing presses to Addis Ababa. But rural Ethiopia remains traditional — village life, subsistence farming, the authority of local lords (ras, dejazmach). Markets in towns like Harar, Gondar, and Jimma are vibrant crossroads of commerce and culture.",
                "cultural_practices": "Timket (Epiphany) is the most spectacular festival — processions of tabot (replicas of the Ark of the Covenant), white-robed crowds, and baptismal ceremonies at rivers and pools. Harar — the walled city in the east — maintains its own Islamic scholarly traditions alongside unique hyena-feeding ceremonies. Coffee from Kaffa and Sidamo regions is exported to the world.",
            },
            "1930s": {
                "events": [
                    "Haile Selassie crowned Emperor (1930) — 'King of Kings, Lord of Lords, Conquering Lion of the Tribe of Judah'",
                    "Italy invades Ethiopia (1935) — use of poison gas, bombing of Red Cross hospitals",
                    "Haile Selassie's address to the League of Nations (1936) — 'It is us today. It will be you tomorrow.'",
                    "Italian occupation (1936–1941) — fierce Ethiopian resistance continues",
                ],
                "daily_life": "The Italian invasion shatters the peace. Poison gas rains on soldiers and civilians. Cities are bombed. A brutal occupation follows — massacres, forced labor, racial segregation. Ethiopian patriots (arbegnoch) wage guerrilla resistance from the mountains. Italians build roads and buildings but at enormous human cost.",
                "cultural_practices": "Resistance culture flourishes — patriotic songs, poetry, and oral histories celebrate the arbegnoch fighters. The Ethiopian Orthodox Church becomes a symbol of national identity and resistance. Despite the occupation, traditional practices — coffee ceremonies, church festivals, family gatherings — maintain cultural continuity in defiance of the occupiers.",
            },
            "1940s": {
                "events": [
                    "Liberation from Italian occupation (1941) with British assistance and Ethiopian patriot forces",
                    "Haile Selassie returns from exile — 'Ethiopia stretches her hands unto God'",
                    "Modernization resumes — new constitution, parliament, university",
                    "Rastafari movement grows in Jamaica, inspired by Haile Selassie's coronation and resistance to colonialism",
                ],
                "daily_life": "Post-liberation rebuilding. Addis Ababa University (then University College) opens. A modern bureaucracy slowly develops alongside the feudal system. Rural landlord-tenant relationships remain unchanged. Coffee exports grow. The Emperor's image appears everywhere.",
                "cultural_practices": "The Ethiopian calendar (13 months of sunshine) and timekeeping (sunrise is 1:00) mark Ethiopian uniqueness. Tej houses (honey wine bars) are social centers. Eskista (shoulder-shaking dance) performed at celebrations. The Ark of the Covenant tradition at Axum's Church of St. Mary of Zion. Ge'ez liturgical chanting with sistrum and prayer staff.",
            },
            "1950s": {
                "events": [
                    "Ethiopia sends troops to fight in the Korean War (Kagnew Battalion)",
                    "Federation with Eritrea (1952)",
                    "Addis Ababa becomes the seat of the UN Economic Commission for Africa",
                    "Haile Selassie becomes a leading pan-African figure",
                    "Rastafari movement in Jamaica venerates Haile Selassie as a divine figure",
                ],
                "daily_life": "Addis Ababa grows into a continental capital — diplomats, students, and travelers from across Africa converge. Ethiopian Airlines connects the country to the world. But most Ethiopians remain rural farmers. Teff cultivation, cattle herding, and the ancient rhythms of highland life continue. Young Ethiopians educated abroad bring back new ideas about equality and change.",
                "cultural_practices": "Ethiopian jazz begins emerging — artists like Mulatu Astatke will soon create a unique fusion of traditional scales with jazz and funk. The coffee ceremony remains the daily social ritual. Ethiopian cuisine — injera and wot (spiced stews) — begins to gain international recognition. Church painting and manuscript traditions continue. Addis Ababa's Mercato (market) becomes the largest open-air market in Africa.",
            },
        },
        "occupations": ["Farming (teff, barley, wheat, coffee, enset)", "Pastoralism (cattle, camels in lowlands)", "Weaving", "Ironwork", "Church scholarship and painting", "Trading (caravans, markets)", "Salt mining (Danakil)", "Coffee cultivation and processing"],
        "trade_patterns": "Ancient trade routes connected the Ethiopian highlands to the Red Sea coast (Adulis, later Massawa) and the Indian Ocean via Harar. Coffee originated in Ethiopia (Kaffa region) and was traded across the Islamic world and then globally. Salt bars (amolé) from the Danakil Depression served as currency. Hide and skin exports. Addis Ababa's Mercato market is the largest in Africa.",
        "diaspora_connections": "The Rastafari connection is uniquely powerful — Haile Selassie's 1966 visit to Jamaica is a sacred event in Rastafari history. Small Rastafari community lives in Shashamane, Ethiopia (land granted by Haile Selassie). Ethiopian diaspora communities exist in Washington DC (the largest Ethiopian population outside Africa), Los Angeles, Seattle, and across Europe. Ethiopian restaurants have become cultural ambassadors worldwide. The Ethiopian Orthodox Church has parishes across the Americas.",
        "migration_patterns": "The 1974 revolution and subsequent Derg regime (Red Terror) created the first major Ethiopian diaspora. Refugee resettlement in the US (especially Washington DC, which now has the largest Ethiopian-born population outside Africa), Europe, and the Middle East. Ongoing migration to the Gulf states and South Africa. Eritrean independence (1993) separated closely related communities.",
    },
}

GENERAL_EAST_AFRICA = {
    "colonial_context": "East Africa experienced successive waves of colonization. The Indian Ocean coast had centuries of Swahili, Arab, and Portuguese trade presence before European colonization. Germany claimed Tanganyika and Rwanda-Burundi, while Britain took Kenya and Uganda. Ethiopia uniquely resisted colonization, defeating Italy at Adwa (1896), though it suffered a brutal Italian occupation (1936–1941). Colonial boundaries divided ethnic groups and imposed new identities, while settler colonialism in Kenya's White Highlands created particularly intense land conflicts.",
    "independence_wave": "Tanganyika's peaceful transition (1961) under Nyerere, Kenya's hard-won independence (1963) after the Mau Mau struggle, and Ethiopia's enduring sovereignty made East Africa a diverse laboratory of post-colonial paths — from ujamaa socialism to capitalist development to imperial continuity.",
    "shared_cultural_elements": [
        "Swahili as a lingua franca and trade language across the region",
        "Indian Ocean trade networks connecting East Africa to Arabia, India, and Persia",
        "Age-set systems organizing social life (Maasai, Kikuyu, Kalenjin, Oromo)",
        "Cattle as wealth, status, and bride-price across pastoralist communities",
        "Coffee culture — Ethiopia as the birthplace of coffee, the ceremony as sacred hospitality",
        "Long-distance caravan trade traditions (Nyamwezi, Kamba)",
        "Swahili architectural heritage — coral stone, carved doors, courtyard houses",
        "Ngoma drumming and dance traditions across diverse ethnic groups",
        "Respect for elders and elaborate age-based social hierarchies",
        "Religious diversity — Christianity (Ethiopian Orthodox, Protestant missions), Islam (coastal Swahili, Somali), and indigenous spiritual practices coexisting",
        "Communal farming and cooperative labor traditions",
        "Beadwork and body adornment as markers of identity and status",
    ],
    "transatlantic_and_indian_ocean_slavery": "While the transatlantic slave trade primarily drew from West Africa, East Africa was the center of the Indian Ocean slave trade. Zanzibar was the largest slave market in East Africa, with enslaved people transported to Oman, the Persian Gulf, India, and the Indian Ocean islands (Mauritius, Réunion, Madagascar). This trade, which peaked in the 19th century, shaped the demography and culture of the entire Indian Ocean world. Ethiopian and Eritrean slaves (habshi) served in Indian courts and armies, and their descendants form communities across South Asia.",
}
