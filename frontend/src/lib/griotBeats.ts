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
 * Timestamps captured via beat-timer.html against the generated audio.
 */
export const GRIOT_BEATS: GriotBeat[] = [
  { time: 0, text: "Come. Sit with me.", duration: 3.2 },
  { time: 3.2, text: "I am a griot \u2014 a keeper of the stories\nthat time tries to scatter.", duration: 5.6 },
  { time: 8.8, text: "For generations, my kind have held the memories\nof families, of kingdoms, of journeys\nno map could ever trace.", duration: 10 },
  { time: 18.8, text: "Tonight, I reach back for you.", duration: 3.8 },
  { time: 22.6, text: "The Akan people have a word \u2014 Sankofa.\nIt means: go back and get it.", duration: 7.9 },
  { time: 30.5, text: "It teaches us that the past is not behind us.\nIt walks beside us, whispering in the language\nof our grandmothers, humming in the rhythms\nour hands remember but our minds have forgotten.", duration: 14 },
  { time: 44.5, text: "Every family has a thread that stretches back \u2014\nthrough oceans crossed and borders redrawn,\nthrough languages that changed shape\nbut never lost their meaning.", duration: 12.2 },
  { time: 56.7, text: "Some of those threads are written in books.\nOthers live only in the land itself,\nin the rhythm of a song,\nin the way a name is spoken.", duration: 10.7 },
  { time: 67.4, text: "Your ancestors lived. They loved.\nThey built. They endured.", duration: 5.5 },
  { time: 72.9, text: "And their story did not end \u2014\nit has been waiting, patient as the baobab,\nfor someone to come and listen.", duration: 8.6 },
  { time: 81.5, text: "So let me gather the threads now.\nLet me listen to what the land remembers,\nwhat the old songs still carry.", duration: 8.8 },
  { time: 90.3, text: "I will weave it all together \u2014\nand you will hear your heritage,\nas it was meant to be told.", duration: 7 },
];
