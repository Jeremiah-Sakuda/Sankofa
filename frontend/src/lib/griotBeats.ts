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
  { time: 3.7, text: "Come. Sit with me.", duration: 5.6 },
  { time: 9.3, text: "I am a griot \u2014 a keeper of the stories\nthat time tries to scatter.", duration: 9.9 },
  { time: 19.3, text: "For generations, my kind have held the memories\nof families, of kingdoms, of journeys\nno map could ever trace.", duration: 3.9 },
  { time: 23.1, text: "Tonight, I reach back for you.", duration: 7.8 },
  { time: 31, text: "The Akan people have a word \u2014 Sankofa.\nIt means: go back and get it.", duration: 14.1 },
  { time: 45, text: "It teaches us that the past is not behind us.\nIt walks beside us, whispering in the language\nof our grandmothers, humming in the rhythms\nour hands remember but our minds have forgotten.", duration: 12.2 },
  { time: 57.2, text: "Every family has a thread that stretches back \u2014\nthrough oceans crossed and borders redrawn,\nthrough languages that changed shape\nbut never lost their meaning.", duration: 10.6 },
  { time: 67.9, text: "Some of those threads are written in books.\nOthers live only in the land itself,\nin the rhythm of a song,\nin the way a name is spoken.", duration: 5.5 },
  { time: 73.4, text: "Your ancestors lived. They loved.\nThey built. They endured.", duration: 8.6 },
  { time: 82, text: "And their story did not end \u2014\nit has been waiting, patient as the baobab,\nfor someone to come and listen.", duration: 8.7 },
  { time: 90.8, text: "So let me gather the threads now.\nLet me listen to what the land remembers,\nwhat the old songs still carry.", duration: 7 },
  { time: 97.8, text: "I will weave it all together \u2014\nand you will hear your heritage,\nas it was meant to be told.", duration: 0 },
];
