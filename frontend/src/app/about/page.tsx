"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import SankofaBird from "../../components/SankofaBird";

export default function AboutPage() {
  const router = useRouter();

  return (
    <div className="relative min-h-screen">
      {/* Fixed background */}
      <div className="fixed inset-0 bg-[var(--night)]" />
      <div className="fixed inset-0 noise-texture pointer-events-none opacity-50" />

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
            href="/"
            className="text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
          >
            Home
          </Link>
        </nav>
      </header>

      {/* Main content */}
      <main className="relative z-10 pt-24 pb-20 px-6">
        <article className="max-w-3xl mx-auto">
          {/* Title */}
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="font-[family-name:var(--font-display)] text-4xl md:text-5xl text-[var(--gold)] tracking-wide mb-4">
              About Sankofa
            </h1>
            <div className="w-24 h-px mx-auto bg-[var(--gold)]/40" />
          </motion.div>

          {/* Why This Exists */}
          <Section title="Why This Exists" delay={0.1}>
            <p>
              I&apos;m first-generation American, born to Kenyan parents. I grew up hearing
              stories — about my family&apos;s region, our name, traditions that traced back
              further than anyone could pinpoint exactly. I had more access to my heritage
              than most people in the diaspora ever get. And still, there were gaps. Entire
              chapters erased by colonial disruption or simply by time. Names no one alive
              remembers. Practices that stopped being practiced and eventually stopped being
              spoken about.
            </p>
            <p>
              That access is a privilege. For millions of people across West African, Caribbean,
              and South Asian diasporas, there are no family stories to start from. There&apos;s
              a surname, maybe a country, maybe nothing. The historical record exists — scattered
              across colonial archives, academic journals, regional oral traditions — but it&apos;s
              inaccessible to the people it belongs to.
            </p>
            <p className="font-[family-name:var(--font-display)] text-[var(--gold)]/80 italic">
              Sankofa was built for that gap.
            </p>
          </Section>

          {/* The Griot Tradition */}
          <Section title="The Griot Tradition" delay={0.2}>
            <p>
              Sankofa is modeled after the West African griot — part historian, part storyteller,
              part musician, part conscience. Griots are the keepers of oral tradition in
              communities across Mali, Senegal, Guinea, and the Gambia. They don&apos;t recite
              facts. They weave together verified history, cultural knowledge, and imaginative
              reconstruction into a living narrative. They control pacing. They know when to
              pause. And they always make clear what&apos;s remembered versus what&apos;s felt.
            </p>
            <p>
              That is the design ethos behind Sankofa. The AI is the griot&apos;s voice. The
              community is the griot&apos;s memory. The user is the listener, welcomed into a
              story that belongs to them.
            </p>
          </Section>

          {/* How Sankofa Tells the Story */}
          <Section title="How Sankofa Tells the Story" delay={0.3}>
            <p>
              Sankofa&apos;s narratives unfold in three acts. Each act contains interleaved text
              and AI-generated watercolor imagery — painted in the warm palette of burnt sienna,
              raw umber, yellow ochre, and gold leaf. Images appear at emotionally resonant
              moments chosen by the AI, not placed mechanically. Voice narration reads each
              segment in a warm storytelling voice. Ambient soundscapes — wind, fire, market,
              drums, nature — cross-fade between acts.
            </p>
            <p>
              After the story ends, the griot remains. You can ask follow-up questions about
              what was left out, what the music of the era sounded like, what daily life looked
              like for the people in your narrative.
            </p>
          </Section>

          {/* Trust Classification */}
          <Section title="Trust Classification" delay={0.4}>
            <p>
              Every segment in every narrative carries one of three tags:
            </p>
            <div className="flex flex-wrap gap-4 my-6">
              <div className="px-4 py-3 border border-[var(--gold)]/40 rounded bg-[var(--gold)]/5">
                <span className="font-[family-name:var(--font-display)] text-[var(--gold)] font-medium">Historical</span>
                <p className="text-sm text-[var(--ivory)]/70 mt-1">Documented facts about the region and era</p>
              </div>
              <div className="px-4 py-3 border border-[var(--ochre)]/40 rounded bg-[var(--ochre)]/5">
                <span className="font-[family-name:var(--font-display)] text-[var(--ochre)] font-medium">Cultural</span>
                <p className="text-sm text-[var(--ivory)]/70 mt-1">Well-documented traditions and practices</p>
              </div>
              <div className="px-4 py-3 border border-[var(--terracotta)]/40 rounded bg-[var(--terracotta)]/5">
                <span className="font-[family-name:var(--font-display)] text-[var(--terracotta)] font-medium">Reconstructed</span>
                <p className="text-sm text-[var(--ivory)]/70 mt-1">Imaginative reconstruction informed by context</p>
              </div>
            </div>
            <p>
              Most AI products hide their uncertainty. Sankofa surfaces it. When users see the
              system being honest about what it knows versus what it imagines, they give it more
              latitude to imagine. Transparency creates permission. Honesty and immersion are
              not in tension.
            </p>
            <p>
              Sankofa will never fabricate specific genealogical claims. It tells the story of
              a place and a people, not a fictional family tree.
            </p>
          </Section>

          {/* The Name */}
          <Section title="The Name" delay={0.5}>
            <p>
              Sankofa is a word in the Akan language of Ghana. It translates literally as
              &ldquo;go back and get it&rdquo; — a teaching that what has been forgotten can
              still be recovered, and that looking backward is not weakness but wisdom.
            </p>
            <p className="font-[family-name:var(--font-display)] text-[var(--ivory)]/80 italic">
              The Akan proverb: Se wo were fi na wosankofa a yenkyi. It is not wrong to go
              back for that which you have forgotten.
            </p>
            <p>
              Sankofa is often represented as a mythical bird looking backward while its feet
              face forward, carrying a precious egg in its beak. The egg is the knowledge being
              recovered.
            </p>
            <div className="flex justify-center my-8">
              <SankofaBird className="w-20 h-20 text-[var(--gold)]/60" />
            </div>
            <p className="text-center text-[var(--muted)] text-sm italic">
              That bird is the logo at the top of every page. The proverb is the closing line
              of every story.
            </p>
          </Section>

          {/* What Sankofa Is Not */}
          <Section title="What Sankofa Is Not" delay={0.6}>
            <ul className="space-y-4">
              <li className="flex gap-3">
                <span className="text-[var(--terracotta)]">&times;</span>
                <span>
                  <strong>Sankofa is not a DNA ancestry test.</strong> It doesn&apos;t tell
                  you what percentage of your genome traces to which region.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="text-[var(--terracotta)]">&times;</span>
                <span>
                  <strong>Sankofa is not a genealogy platform.</strong> It doesn&apos;t build
                  family trees from records.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="text-[var(--terracotta)]">&times;</span>
                <span>
                  <strong>Sankofa is not a replacement for family.</strong> If you have living
                  relatives who carry oral history, talk to them first. Sankofa is for the
                  gaps they can&apos;t fill.
                </span>
              </li>
            </ul>
          </Section>

          {/* Recognition */}
          <Section title="Recognition" delay={0.7}>
            <p>
              Sankofa won the <strong>Creative Storytellers</strong> category in Google&apos;s
              Gemini Live Agent Challenge, selected from 11,896 participants. It was presented
              at <strong>Google Cloud Next 2026</strong> in Las Vegas.
            </p>
          </Section>

          {/* The Promise */}
          <Section title="The Promise" delay={0.8}>
            <p>
              Sankofa is free for anyone to use for their first story. The mission — making
              heritage accessible to diaspora communities worldwide — is not compatible with
              paywalls on the front door.
            </p>
            <p>
              Future features for returning users (saved heritage libraries, multi-generational
              narratives, family collaboration) may be paid. The griot will always tell your
              first story for free.
            </p>
          </Section>

          {/* Open Source */}
          <Section title="Open Source" delay={0.9}>
            <p>
              Sankofa is open source under the AGPL-3.0 license. The code is available at{" "}
              <a
                href="https://github.com/Jeremiah-Sakuda/Sankofa"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--gold)] hover:underline"
              >
                github.com/Jeremiah-Sakuda/Sankofa
              </a>
              . Community contributions to the knowledge base are welcome — the griot&apos;s
              memory grows with everyone who gives back to it.
            </p>
          </Section>

          {/* Final CTA */}
          <motion.div
            className="mt-20 pt-12 border-t border-[var(--gold)]/20 text-center"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <motion.button
              onClick={() => router.push("/")}
              className="px-10 py-4 border border-[var(--gold)] bg-[var(--gold)] text-[var(--night)] font-[family-name:var(--font-display)] text-lg tracking-[0.1em] uppercase transition-all duration-500 hover:bg-transparent hover:text-[var(--gold)] cursor-pointer"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              Begin Your Journey
            </motion.button>
          </motion.div>
        </article>
      </main>
    </div>
  );
}

function Section({
  title,
  children,
  delay = 0,
}: {
  title: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.section
      className="mb-14"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.6, delay }}
    >
      <h2 className="font-[family-name:var(--font-display)] text-2xl md:text-3xl text-[var(--gold)] tracking-wide mb-6">
        {title}
      </h2>
      <div className="font-[family-name:var(--font-body)] text-base md:text-lg text-[var(--ivory)]/90 leading-relaxed space-y-4">
        {children}
      </div>
    </motion.section>
  );
}
