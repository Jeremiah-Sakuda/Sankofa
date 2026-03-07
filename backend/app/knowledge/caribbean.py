"""
Cultural knowledge base for Caribbean regions.
"""

REGIONS = {
    "jamaica": {
        "name": "Jamaica",
        "modern_name": "Jamaica",
        "colonial_name": "British Jamaica",
        "languages": ["Jamaican Patois (Creole)", "English"],
        "ethnic_groups": ["Afro-Jamaican", "Indo-Jamaican", "Chinese-Jamaican", "Mixed/Multiracial"],
        "geography": "Mountainous island in the Caribbean Sea. Blue Mountains in the east rise to 2,256m. Lush tropical vegetation, white sand beaches, and limestone karst terrain. Kingston sits on a natural harbor on the southeast coast.",
        "decades": {
            "1940s": {
                "events": [
                    "Jamaican soldiers serve in WWII with the Caribbean Regiment",
                    "Labour movement gains momentum under Alexander Bustamante and Norman Manley",
                    "Universal adult suffrage granted in 1944",
                    "Banana and sugar exports drive the economy",
                ],
                "daily_life": "Rural life centers on small farming (provision grounds) and sugar estate labor. Market women (higglers) dominate internal trade. Family life organized around the yard — a communal outdoor space shared by extended family. Kingston grows as people migrate from rural parishes.",
                "cultural_practices": "Revival and Kumina spiritual traditions maintain African religious continuity. Mento music — the precursor to ska and reggae — played at gatherings. Anansi stories told to children. Nine Night ceremonies for the dead. Christmas Jonkanoo masquerade parades.",
            },
            "1950s": {
                "events": [
                    "West Indies Federation formed (1958)",
                    "Mass migration to Britain (Windrush generation, starting 1948)",
                    "Rastafari movement grows",
                    "Jamaica gains independence in 1962",
                ],
                "daily_life": "Thousands migrate to Britain seeking opportunity — the Windrush generation transforms both Jamaica and the UK. Back home, urbanization accelerates. Sound system culture emerges in Kingston's dancehalls. Ska music is born.",
                "cultural_practices": "Sound system dances become the center of youth culture. Rastafari develops as a spiritual and cultural movement. Cricket becomes a national obsession. Sunday dinners of rice and peas, jerk chicken, and ackee and saltfish anchor family life.",
            },
        },
        "occupations": ["Sugar plantation labor", "Small farming", "Fishing", "Domestic service", "Trading (higglers)", "Dockwork", "Bauxite mining", "Teaching"],
        "trade_patterns": "Sugar, bananas, and bauxite as primary exports. Internal market system dominated by higglers. Trade connections to Britain, Canada, and the United States.",
        "diaspora_connections": "Jamaican culture has had outsized global influence through reggae music, Rastafari, and cuisine. Large diaspora communities in the UK (Windrush generation and descendants), New York, Miami, Toronto, and across Central America (Costa Rica, Panama — descendants of canal workers). Maroon communities in Jamaica maintain direct cultural links to West African (Akan) heritage.",
        "migration_patterns": "Windrush migration to UK (1948-1971). Continued migration to US (New York, Miami), Canada (Toronto), and later return migration. Internal migration from rural parishes to Kingston.",
    },
    "haiti": {
        "name": "Haiti",
        "modern_name": "Haiti",
        "colonial_name": "Saint-Domingue (French)",
        "languages": ["Haitian Creole", "French"],
        "ethnic_groups": ["Afro-Haitian", "Mulatto"],
        "geography": "Western third of the island of Hispaniola. Mountainous terrain with the Massif de la Hotte and Massif de la Selle. Subtropical climate. Port-au-Prince sits in a bay surrounded by mountains.",
        "decades": {
            "1940s": {
                "events": [
                    "End of US occupation (1934) still shapes politics",
                    "Élie Lescot and Dumarsais Estimé presidencies",
                    "Anti-superstition campaign targets Vodou practitioners",
                    "Literary and cultural renaissance — négritude movement in Haiti",
                ],
                "daily_life": "Rural peasant farming (coffee, sugarcane, mangoes) on small plots. Communal work groups (konbit) maintain African cooperative traditions. Port-au-Prince grows but remains connected to rural origins. Market women (Madan Sara) are the backbone of the economy.",
                "cultural_practices": "Vodou is the heartbeat of Haitian culture — ceremonies, healing, community. Rara festival processions during Lent. Oral storytelling tradition (Krik? Krak!). Haitian art — vibrant painting tradition born in this era. Iron sculpture from oil drums.",
            },
        },
        "occupations": ["Peasant farming", "Market trading (Madan Sara)", "Fishing", "Artisan crafts", "Coffee cultivation", "Domestic service"],
        "trade_patterns": "Coffee and sugar exports. Internal market system connecting rural areas to Port-au-Prince. Informal cross-border trade with Dominican Republic.",
        "diaspora_connections": "Haiti was the first free Black republic (1804), born of the only successful large-scale slave revolt. This history resonates across the African diaspora. Large Haitian communities in New York (Flatbush), Miami (Little Haiti), Montreal, and Paris. Vodou traditions directly connect to Fon and Ewe religious practices from Dahomey (Benin). Haitian Creole preserves significant West African linguistic elements.",
        "migration_patterns": "Migration to Cuba and Dominican Republic for sugar work. Post-Duvalier migration to US and Canada. Boat migration to Florida. Professional class migration to Francophone Africa (Congo, Senegal) as educators and administrators.",
    },
    "trinidad": {
        "name": "Trinidad and Tobago",
        "modern_name": "Trinidad and Tobago",
        "colonial_name": "British Trinidad and Tobago",
        "languages": ["Trinidad Creole English", "Trinidad Bhojpuri", "English"],
        "ethnic_groups": ["Afro-Trinidadian", "Indo-Trinidadian", "Mixed", "Chinese-Trinidadian", "Syrian/Lebanese"],
        "geography": "Southernmost Caribbean island, just off the coast of Venezuela. Trinidad is flat to rolling in the south with the Northern Range mountains. Tropical rainforest, mangrove swamps, and the famous Pitch Lake.",
        "decades": {
            "1940s": {
                "events": [
                    "US military bases transform the economy during WWII",
                    "Oil industry grows",
                    "Labour unrest and rise of trade unions",
                    "Calypso tents flourish as political commentary",
                ],
                "daily_life": "A uniquely multi-ethnic society — African, Indian, Chinese, Syrian, and European communities coexist. Oil and sugar drive the economy. US military presence brings dollars and cultural exchange. Calypso music is the voice of the people.",
                "cultural_practices": "Carnival — the greatest street festival in the Caribbean. Steelpan (steel drum) invented from oil barrels. Calypso as political satire and social commentary. Hindu and Muslim festivals alongside Christian and African-derived celebrations. Limbo, stick-fighting (kalinda), and Orisha traditions.",
            },
        },
        "occupations": ["Oil refinery work", "Sugar estate labor", "Civil service", "Trading", "Fishing", "Cocoa farming", "Music/entertainment"],
        "trade_patterns": "Oil and natural gas exports dominate. Sugar and cocoa as agricultural exports. Trade connections to Venezuela, other Caribbean islands, UK, and US.",
        "diaspora_connections": "Trinidadian culture has global influence through Carnival, steelpan, calypso, and soca music. Diaspora communities in New York, London, Toronto, and throughout the Caribbean. Unique Afro-Indian cultural blend found nowhere else. Orisha tradition connects to Yoruba heritage.",
        "migration_patterns": "Migration to UK, US (New York), and Canada (Toronto). Oil-boom era attracted workers from other Caribbean islands. Significant brain drain of professionals.",
    },
}
