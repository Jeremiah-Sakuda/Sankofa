"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import SankofaBird from "../../components/SankofaBird";
import GoldParticles from "../../components/GoldParticles";

interface Region {
  id: string;
  name: string;
  modernName: string;
  colonialName: string;
  coverageEras: string[];
  languages: string[];
  description: string;
}

interface RegionGroup {
  name: string;
  description: string;
  regions: Region[];
}

const REGION_DATA: RegionGroup[] = [
  {
    name: "West Africa",
    description: "The cradle of griots, kingdoms, and the majority of the transatlantic diaspora",
    regions: [
      {
        id: "ghana",
        name: "Gold Coast / Ghana",
        modernName: "Ghana",
        colonialName: "Gold Coast",
        coverageEras: ["1900s", "1910s", "1920s", "1930s", "1940s", "1950s"],
        languages: ["Akan (Twi, Fante)", "Ewe", "Ga"],
        description: "Ashanti gold, kente cloth, and the first sub-Saharan nation to achieve independence. Home of Sankofa.",
      },
      {
        id: "nigeria",
        name: "Yorubaland / Nigeria",
        modernName: "Nigeria",
        colonialName: "British Nigeria",
        coverageEras: ["1900s", "1920s", "1940s", "1950s"],
        languages: ["Yoruba", "Igbo", "Hausa"],
        description: "Yoruba kingdoms, Igbo enterprise, and the birthplace of Afrobeat. One of Africa's most populous nations.",
      },
      {
        id: "senegambia",
        name: "Senegambia",
        modernName: "Senegal and The Gambia",
        colonialName: "French West Africa / British Gambia",
        coverageEras: ["1940s", "1950s"],
        languages: ["Wolof", "Mandinka", "Pulaar"],
        description: "The griot tradition's heartland. Gorée Island, the Roots connection, and the birthplace of mbalax.",
      },
      {
        id: "dahomey",
        name: "Dahomey / Benin",
        modernName: "Benin Republic",
        colonialName: "French Dahomey",
        coverageEras: ["1940s"],
        languages: ["Fon", "Yoruba"],
        description: "The Dahomey Amazons, Vodun's birthplace, and the Door of No Return at Ouidah.",
      },
      {
        id: "sierra-leone",
        name: "Sierra Leone",
        modernName: "Sierra Leone",
        colonialName: "British Sierra Leone",
        coverageEras: ["1940s"],
        languages: ["Krio", "Temne", "Mende"],
        description: "Founded by freed slaves, home of Krio culture and the Lion Mountains.",
      },
    ],
  },
  {
    name: "East Africa",
    description: "Swahili coasts, highland kingdoms, and the cradle of humanity",
    regions: [
      {
        id: "kenya",
        name: "Kenya",
        modernName: "Kenya",
        colonialName: "British East Africa",
        coverageEras: ["1900s", "1910s", "1920s", "1930s", "1940s", "1950s"],
        languages: ["Swahili", "Kikuyu", "Luo", "Maasai"],
        description: "Maasai warriors, Mau Mau resistance, and the uhuru spirit. From Mombasa's ancient ports to the Rift Valley.",
      },
      {
        id: "tanzania",
        name: "Tanganyika / Tanzania",
        modernName: "Tanzania",
        colonialName: "German East Africa / British Mandate",
        coverageEras: ["1900s", "1910s", "1920s", "1930s", "1940s", "1950s"],
        languages: ["Swahili", "Sukuma", "Chagga"],
        description: "Zanzibar spices, Kilimanjaro's peaks, and Nyerere's ujamaa vision of African socialism.",
      },
      {
        id: "ethiopia",
        name: "Ethiopia / Abyssinia",
        modernName: "Ethiopia",
        colonialName: "Never colonized (Italian occupation 1936-1941)",
        coverageEras: ["1900s", "1910s", "1920s", "1930s", "1940s", "1950s"],
        languages: ["Amharic", "Oromo", "Tigrinya"],
        description: "The unconquered empire. Birthplace of coffee, the Ark's resting place, and Rastafari's Zion.",
      },
    ],
  },
  {
    name: "Caribbean",
    description: "Where African roots took new form across the Middle Passage",
    regions: [
      {
        id: "jamaica",
        name: "Jamaica",
        modernName: "Jamaica",
        colonialName: "British Jamaica",
        coverageEras: ["1940s", "1950s"],
        languages: ["Jamaican Patois", "English"],
        description: "Maroon resistance, reggae rhythms, and Rastafari spirituality. The Windrush generation's homeland.",
      },
      {
        id: "haiti",
        name: "Haiti",
        modernName: "Haiti",
        colonialName: "Saint-Domingue (French)",
        coverageEras: ["1940s"],
        languages: ["Haitian Creole", "French"],
        description: "The first free Black republic, born of revolution. Vodou, konbit, and unbreakable spirit.",
      },
      {
        id: "trinidad",
        name: "Trinidad and Tobago",
        modernName: "Trinidad and Tobago",
        colonialName: "British Trinidad",
        coverageEras: ["1940s"],
        languages: ["Trinidad Creole", "English"],
        description: "Carnival's birthplace, steelpan's invention, and a unique African-Indian cultural fusion.",
      },
    ],
  },
  {
    name: "South Asia",
    description: "Ancient lands, partition wounds, and global diaspora",
    regions: [
      {
        id: "punjab",
        name: "Punjab",
        modernName: "India (Punjab) and Pakistan",
        colonialName: "British India",
        coverageEras: ["1940s"],
        languages: ["Punjabi", "Hindi", "Urdu"],
        description: "Land of five rivers, Partition's deepest wound, and bhangra's heartbeat.",
      },
      {
        id: "bengal",
        name: "Bengal",
        modernName: "India (West Bengal) and Bangladesh",
        colonialName: "Bengal Presidency",
        coverageEras: ["1940s"],
        languages: ["Bengali"],
        description: "Tagore's homeland, the world's largest delta, and the 1943 famine's memory.",
      },
    ],
  },
];

function RegionCard({ region, index }: { region: Region; index: number }) {
  const router = useRouter();
  const coverageCount = region.coverageEras.length;
  const coverageLabel = coverageCount >= 5 ? "Deep" : coverageCount >= 3 ? "Moderate" : "Focused";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="group relative border border-[var(--gold)]/20 bg-[var(--night)]/50 backdrop-blur-sm p-6 hover:border-[var(--gold)]/40 transition-all duration-300 cursor-pointer"
      onClick={() => router.push(`/?region=${encodeURIComponent(region.modernName)}`)}
    >
      {/* Coverage indicator */}
      <div className="absolute top-4 right-4">
        <span className={`text-xs tracking-wider uppercase px-2 py-1 ${
          coverageLabel === "Deep"
            ? "text-[var(--gold)] bg-[var(--gold)]/10 border border-[var(--gold)]/30"
            : coverageLabel === "Moderate"
            ? "text-[var(--ochre)] bg-[var(--ochre)]/10 border border-[var(--ochre)]/30"
            : "text-[var(--muted)] bg-[var(--muted)]/10 border border-[var(--muted)]/30"
        }`}>
          {coverageLabel}
        </span>
      </div>

      <h3 className="font-[family-name:var(--font-display)] text-xl text-[var(--gold)] mb-1 pr-20">
        {region.name}
      </h3>

      <p className="text-xs text-[var(--muted)] mb-3">
        {region.colonialName}
      </p>

      <p className="font-[family-name:var(--font-body)] text-sm text-[var(--ivory)]/80 mb-4 leading-relaxed">
        {region.description}
      </p>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-1">
          {region.coverageEras.map((era) => (
            <span
              key={era}
              className="text-xs px-2 py-0.5 bg-[var(--gold)]/5 text-[var(--gold)]/70 border border-[var(--gold)]/20"
            >
              {era}
            </span>
          ))}
        </div>

        <p className="text-xs text-[var(--muted)]">
          {region.languages.slice(0, 3).join(" · ")}
          {region.languages.length > 3 && ` +${region.languages.length - 3}`}
        </p>
      </div>

      {/* Hover indicator */}
      <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-xs text-[var(--gold)] tracking-wider">
          Begin →
        </span>
      </div>
    </motion.div>
  );
}

function RegionGroupSection({ group, groupIndex }: { group: RegionGroup; groupIndex: number }) {
  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, amount: 0.1 }}
      transition={{ duration: 0.6 }}
      className="mb-16"
    >
      <div className="mb-8">
        <h2 className="font-[family-name:var(--font-display)] text-2xl md:text-3xl text-[var(--gold)] tracking-wide mb-2">
          {group.name}
        </h2>
        <p className="font-[family-name:var(--font-body)] text-[var(--muted)] italic">
          {group.description}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {group.regions.map((region, index) => (
          <RegionCard key={region.id} region={region} index={index} />
        ))}
      </div>
    </motion.section>
  );
}

export default function ExplorePage() {
  return (
    <div className="relative min-h-screen">
      {/* Fixed background */}
      <div className="fixed inset-0 bg-[var(--night)] animate-gradient-drift bg-gradient-to-br from-[var(--night)] via-[var(--indigo)] to-[#1a0f0a]" />
      <div className="fixed inset-0 noise-texture pointer-events-none opacity-50" />
      <GoldParticles count={20} />

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-20 px-6 py-4 flex items-center justify-between bg-[var(--night)]/80 backdrop-blur-sm border-b border-[var(--gold)]/10">
        <Link href="/" className="flex items-center gap-3 group">
          <SankofaBird className="w-6 h-6 text-[var(--gold)] group-hover:scale-110 transition-transform" />
          <span className="font-[family-name:var(--font-display)] text-lg tracking-wider text-[var(--gold)]">
            Sankofa
          </span>
        </Link>
        <nav className="flex items-center gap-6">
          <Link
            href="/about"
            className="text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
          >
            About
          </Link>
          <Link
            href="/"
            className="text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
          >
            Home
          </Link>
        </nav>
      </header>

      {/* Main content */}
      <main className="relative z-10 pt-24 pb-20 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Title */}
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="font-[family-name:var(--font-display)] text-4xl md:text-5xl text-[var(--gold)] tracking-wide mb-4">
              Explore Regions
            </h1>
            <p className="font-[family-name:var(--font-body)] text-lg text-[var(--ivory)]/80 max-w-2xl mx-auto">
              The griot&apos;s knowledge spans four continents and centuries of history.
              Choose a region to begin your heritage narrative.
            </p>
            <div className="w-24 h-px mx-auto bg-[var(--gold)]/40 mt-6" />
          </motion.div>

          {/* Coverage legend */}
          <motion.div
            className="flex flex-wrap justify-center gap-6 mb-12 text-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 text-xs text-[var(--gold)] bg-[var(--gold)]/10 border border-[var(--gold)]/30">
                Deep
              </span>
              <span className="text-[var(--muted)]">5+ decades documented</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 text-xs text-[var(--ochre)] bg-[var(--ochre)]/10 border border-[var(--ochre)]/30">
                Moderate
              </span>
              <span className="text-[var(--muted)]">3-4 decades</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 text-xs text-[var(--muted)] bg-[var(--muted)]/10 border border-[var(--muted)]/30">
                Focused
              </span>
              <span className="text-[var(--muted)]">1-2 decades</span>
            </div>
          </motion.div>

          {/* Region groups */}
          {REGION_DATA.map((group, index) => (
            <RegionGroupSection key={group.name} group={group} groupIndex={index} />
          ))}

          {/* Footer note */}
          <motion.div
            className="mt-16 pt-8 border-t border-[var(--gold)]/20 text-center"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <p className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] mb-4">
              Don&apos;t see your region? The griot draws on broader knowledge too.
            </p>
            <Link
              href="/"
              className="inline-block px-6 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all"
            >
              Begin With Any Region
            </Link>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
