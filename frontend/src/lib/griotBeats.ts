export interface GriotBeat {
  /** Seconds from audio start when this line appears */
  time: number;
  /** Text to display on screen */
  text: string;
  /** How long this line stays visible (seconds) */
  duration: number;
}

/**
 * Timestamped text beats synchronized with griot-intro.wav.
 *
 * These timestamps are estimates based on ~210 words at griot cadence
 * (~2.2 words/sec with pauses). Fine-tune after generating the audio.
 */
export const GRIOT_BEATS: GriotBeat[] = [
  {
    time: 0,
    text: "Come. Sit with me.",
    duration: 4,
  },
  {
    time: 5,
    text: "I am a griot \u2014 a keeper of the stories\nthat time tries to scatter.",
    duration: 7,
  },
  {
    time: 13,
    text: "For generations, my kind have held the memories\nof families, of kingdoms, of journeys\nno map could ever trace.",
    duration: 8,
  },
  {
    time: 22,
    text: "Tonight, I reach back for you.",
    duration: 4,
  },
  {
    time: 27,
    text: "The Akan people have a word \u2014 Sankofa.\nIt means: go back and get it.",
    duration: 7,
  },
  {
    time: 35,
    text: "It teaches us that the past is not behind us.\nIt walks beside us, whispering in the language\nof our grandmothers.",
    duration: 9,
  },
  {
    time: 45,
    text: "Every family has a thread that stretches back \u2014\nthrough oceans crossed and borders redrawn.",
    duration: 8,
  },
  {
    time: 54,
    text: "Some of those threads are written in books.\nOthers live only in the land itself,\nin the rhythm of a song,\nin the way a name is spoken.",
    duration: 10,
  },
  {
    time: 65,
    text: "Your ancestors lived. They loved.\nThey built. They endured.",
    duration: 7,
  },
  {
    time: 73,
    text: "And their story did not end \u2014\nit has been waiting, patient as the baobab,\nfor someone to come and listen.",
    duration: 9,
  },
  {
    time: 83,
    text: "So let me gather the threads now.\nLet me listen to what the land remembers,\nwhat the old songs still carry.",
    duration: 9,
  },
  {
    time: 93,
    text: "I will weave it all together \u2014\nand you will hear your heritage,\nas it was meant to be told.",
    duration: 8,
  },
];
