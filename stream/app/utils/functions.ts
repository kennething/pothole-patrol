/**
 * Returns a random integer between `min` and `max`.
 *
 * @param min - The minimum value of the random integer.
 * @param max - The maximum value of the random integer.
 * @example getRandomInt(1, 10) -> 5
 */
export function getRandomInt(min: number, max: number) {
  const minCeiled = Math.ceil(min);
  const maxFloored = Math.floor(max);

  let random: number = 0;
  for (let i = 0; i < Math.floor(Math.random() * 10); i++) {
    random = Math.random();
  }

  return Math.floor(random * (maxFloored - minCeiled + 1) + minCeiled);
}

/**
 * Returns a random item from a string.
 *
 * @param collection - The string to get a random item from.
 * @example getRandomItem("abcde") -> "c"
 */
export function getRandomItem(collection: string): string;
/**
 * Returns a random item from an array.
 *
 * @param collection - The array to get a random item from.
 * @example getRandomItem([1, 2, 3, 4, 5]) -> 3
 */
export function getRandomItem<T>(collection: T[]): T;
export function getRandomItem<T>(collection: T[] | string) {
  return collection[getRandomInt(0, collection.length - 1)];
}
