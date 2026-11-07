import { existsSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";

const projectRoot = process.cwd();

const eventsFile = join(projectRoot, "utils", "events.ts");
const outputPath = join(projectRoot, "..", "stream", "app", "utils", "events.ts");

let content = `// ! This file is auto-generated. Do not edit directly.
// ? 
// ?                                                   |    |
// ?   ..._  ___                                       |    |
// ?  \`."".\`''''""--..___                              |    |
// ?  ,-\\  \\             ""-...__         _____________/    |
// ?  / \` " '                    \`""""""""                  .
// ?  \\                                                      L
// ?  (>                                                      \\
// ? /                                                         \\
// ? \\_    ___..---.                                            L
// ?   \`--'         '.                                           \\
// ?                  .                                           \\_
// ?                 _/\`.                                           \`.._
// ?              .'     -.                                             \`.
// ?             /     __.-Y     /''''''-...___,...--------.._            |
// ?            /   _."    |    /                ' .      \\   '---..._    |
// ?           /   /      /    /                _,. '    ,/           |   |
// ?           \\_,'     _.'   /              /''     _,-'            _|   |
// ?                   '     /               \`-----''               /     |
// ?                   \`...-'
`;
if (existsSync(eventsFile)) {
  content += readFileSync(eventsFile, "utf8");
  content = content
    .split("\n")
    .filter((line) => !line.startsWith("import"))
    .join("\n");
}

writeFileSync(outputPath, content);
