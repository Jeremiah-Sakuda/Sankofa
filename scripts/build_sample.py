import base64
import json
import os

# Image paths
img1 = r"C:\Users\jerem\Desktop\2025 Fall Projects\Sankofa\media\Example image 1.png"
img2 = r"C:\Users\jerem\Desktop\2025 Fall Projects\Sankofa\media\Example image 2.png"
img3 = r"C:\Users\jerem\Desktop\2025 Fall Projects\Sankofa\media\Example Image 3.png"

def encode_image(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

# Encode images
img1_b64 = encode_image(img1)
img2_b64 = encode_image(img2)
img3_b64 = encode_image(img3)

# Text segments from the user's narrative
act1_text1 = """Ah, listen closely, my child, and let Sankofa, your griot, open the calabash of memory. We journey now to the sun-drenched plains of Kenya, to the land of the Maasai, in the year of our ancestors, 1940. The winds that swept across those vast rangelands carried not only the scent of acacia and dust but also the faint whispers of a world in turmoil, though far removed from the daily rhythms of the Sakuda family. Their lives, like the mighty herds of cattle they tended, were a testament to ancient traditions, a vibrant tapestry woven with the threads of the earth and the sky. For the Maasai, cattle were more than mere beasts; they were the very pulse of life, the walking embodiment of wealth, status, and sustenance. A man's prosperity was measured in the size and health of his herd, each cow a living symbol of blessing and a bond to the ancestors. From their milk and blood, the Maasai drew strength, from their hides, their homes and clothing. The rhythm of their days was dictated by the needs of these magnificent creatures, moving across the landscape in search of verdant pastures, a nomadic dance as old as time itself."""

act1_text2 = """Yet, even in these seemingly untouched expanses, the shadow of the colonial administration stretched long, slowly, inexorably, tightening its grip on the ancestral lands. The traditional patterns of movement, the very essence of Maasai pastoralism, began to feel the subtle pressure of boundaries drawn by foreign hands, boundaries that made little sense to a people whose home was the horizon. The vastness of the plains, once boundless, now held an invisible tension, a quiet hum beneath the rustling grass, portending changes yet to fully unfold."""

act2_text1 = """Ah, my child, let the drums begin to beat now, a steady rhythm that quickens the heart, for we step deeper into the story of the Sakuda, into the very pulse of their community. The sun climbs high, and the daily life of the Maasai unfolds with vibrant energy. Here, the age-set system, ancient and sacred, dictated the path of every young man. To be a moran, a warrior, was to walk a path of immense responsibility, of bravery tested under the fierce sun, and a deep, abiding commitment to the well-being of the olale—the community. These were the protectors, their lean bodies adorned with ochre and intricate beadwork, their spears glinting like promises in the sunlight. They moved with a proud grace, embodying the strength and spirit of their people, their lives a living testament to courage and communal duty."""

act2_text2 = """But the plains were no longer just for the moran and their cattle. The echoes of a far-off war, the one they called "World War Two," began to manifest in human form. From distant lands, some Maasai sons, and others from neighboring tribes, began to return, their eyes having seen things beyond the savanna, their ears having heard the roar of cannons instead of lions. These returning soldiers, though few, carried with them not only new scars but also new ideas, a sharpened awareness of the injustices woven into the fabric of colonial rule. They had fought for the King's empire, yet returned to find their own people increasingly dispossessed, their ancestral lands shrinking under the relentless 'land hunger' of the settlers and the administration. A new kind of drum began to beat in their hearts—the drum of political awakening. It was amidst this growing unease that the whispers of the Kenya African Union began to spread, like a dry season fire fanned by the wind. A new seed of unity, of demanding what was rightfully theirs, was being sown in the fertile soil of discontent. The elders of the Sakuda, gathered under the wide sky, would speak in hushed tones of the changing times, of the tightening circle around their grazing lands, and the unfair taxes that sought to break their spirit. While their daily lives continued, guided by the sun and the needs of their herds, a new current flowed beneath the surface, a gathering storm of awareness and a yearning for self-determination that would soon change the destiny of all who lived on those magnificent plains."""

act3_text1 = """Ah, the fire now crackles and dances, my children, illuminating the faces of those who listen, for we come to the heart of the matter, the enduring spirit that binds the Sakuda to their past and guides their future. The winds of change may howl, and the drums of discontent may beat, but the Maasai spirit, like the ancient acacia, roots itself ever deeper into the earth of their ancestors. In the hands of Sakuda women, the stories of their people were not merely spoken but meticulously crafted, bead by vibrant bead. Behold the enkarewa, the broad, flat collar, or the delicate isurutia adorning the ears of a young maiden. Each tiny glass bead, carefully chosen and strung, was a word in a silent language, a symbol of status, age, marital state, and the very narrative of a life lived under the vast Kenyan sky. The reds spoke of bravery and blood, the blues of the sky and the rains, the greens of the nourishing grasses, and the whites of purity. These were not mere ornaments; they were living tapestries of identity, portable histories that connected the wearer to generations past, reminding them of who they were and where they came from, even as the world around them shifted on its axis."""

act3_text2 = """Even as the colonial government tightened its grip, even as the best grazing lands were carved away for settlers, the Sakuda, like all Maasai, clung fiercely to their ancestral ways. The displacement from traditional territories was a cruel blow, forcing communities into smaller, often less fertile reserves. Yet, in the face of such adversity, their communal bonds strengthened. The sharing of cattle, the collective responsibility for the manyatta, the intricate web of kinship and mutual support—these practices became their shield and their anchor. They performed their sacred ceremonies, initiated their young warriors, and celebrated their harvests, not in defiance, but as an affirmation of their very being. The external pressures of the 1940s, the land hunger and the nascent political stirrings, only served to highlight the profound resilience of a people determined to preserve their essence. And so, the ancestral thread, shimmering like a golden strand woven into the very fabric of their existence, continued to guide the Sakuda. It was the wisdom of their forebears, passed down through proverbs and stories told around the evening fire, that reminded them of their strength, their connection to the land, and their unbreakable spirit. The challenges of the 1940s were immense, threatening to unravel the tapestry of their lives, but the Sakuda held firm. They understood that their identity was not just in the cattle they herded, nor in the lands they grazed, but in the enduring legacy of their ancestors—a legacy of pride, resilience, and an unwavering commitment to their unique way of life. The fires of change might burn, but the ember of their heritage glowed ever brighter, a promise of continuity for generations yet to come."""

# Build segments
segments = []
seq = 0

# Act 1
segments.append({
    "type": "text",
    "content": act1_text1,
    "media_data": None,
    "media_type": None,
    "trust_level": "cultural",
    "sequence": seq,
    "act": 1,
    "is_hero": False
})
seq += 1

segments.append({
    "type": "image",
    "content": "Maasai herders walking with their cattle across the golden Kenyan plains at sunset, with acacia trees in the background. Watercolor illustration in warm earth tones.",
    "media_data": img1_b64,
    "media_type": "image/png",
    "trust_level": "cultural",
    "sequence": seq,
    "act": 1,
    "is_hero": True
})
seq += 1

segments.append({
    "type": "text",
    "content": act1_text2,
    "media_data": None,
    "media_type": None,
    "trust_level": "cultural",
    "sequence": seq,
    "act": 1,
    "is_hero": False
})
seq += 1

# Act 2
segments.append({
    "type": "text",
    "content": act2_text1,
    "media_data": None,
    "media_type": None,
    "trust_level": "cultural",
    "sequence": seq,
    "act": 2,
    "is_hero": False
})
seq += 1

segments.append({
    "type": "image",
    "content": "Maasai warriors (moran) standing proud on the savanna with spears, alongside returning soldiers in military uniforms, representing the intersection of tradition and World War II's impact. Watercolor illustration.",
    "media_data": img2_b64,
    "media_type": "image/png",
    "trust_level": "historical",
    "sequence": seq,
    "act": 2,
    "is_hero": False
})
seq += 1

segments.append({
    "type": "text",
    "content": act2_text2,
    "media_data": None,
    "media_type": None,
    "trust_level": "historical",
    "sequence": seq,
    "act": 2,
    "is_hero": False
})
seq += 1

# Act 3
segments.append({
    "type": "text",
    "content": act3_text1,
    "media_data": None,
    "media_type": None,
    "trust_level": "cultural",
    "sequence": seq,
    "act": 3,
    "is_hero": False
})
seq += 1

segments.append({
    "type": "image",
    "content": "Maasai women engaged in traditional beadwork under an acacia tree, with a young girl watching and learning. Their colorful beaded collars (enkarewa) and clothing glow in warm sunlight. Watercolor illustration.",
    "media_data": img3_b64,
    "media_type": "image/png",
    "trust_level": "historical",
    "sequence": seq,
    "act": 3,
    "is_hero": False
})
seq += 1

segments.append({
    "type": "text",
    "content": act3_text2,
    "media_data": None,
    "media_type": None,
    "trust_level": "cultural",
    "sequence": seq,
    "act": 3,
    "is_hero": False
})

# Build full structure
sample = {
    "user_input": {
        "family_name": "Sakuda",
        "region_of_origin": "Kenya",
        "time_period": "1940s",
        "known_facts": "Maasai pastoralists, cattle herders",
        "cultural_details": "Traditional Maasai customs, age-set system, beadwork traditions"
    },
    "segments": segments
}

# Write to file
output_path = r"C:\Users\jerem\Desktop\2025 Fall Projects\Sankofa\backend\app\data\sample_narrative.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(sample, f, indent=2, ensure_ascii=False)

print(f"Created sample narrative with {len(segments)} segments")
print(f"Image sizes: {len(img1_b64)}, {len(img2_b64)}, {len(img3_b64)} bytes base64")
