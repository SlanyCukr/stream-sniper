import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const productionRoots = ["app", "components", "contexts", "hooks", "lib", "utils", "views"];
const boundaryConfig = JSON.parse(fs.readFileSync(path.join(root, "tsconfig.checkjs-boundaries.json"), "utf8"));
const baseline = JSON.parse(fs.readFileSync(path.join(root, "type-migration-baseline.json"), "utf8"));

function javascriptFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return javascriptFiles(entryPath);
    return /\.jsx?$/.test(entry.name) ? [path.relative(root, entryPath).replaceAll(path.sep, "/")] : [];
  });
}

const productionFiles = new Set(productionRoots.flatMap((directory) => javascriptFiles(path.join(root, directory))));
const checkedFiles = new Set(
  boundaryConfig.include.filter((file) => /\.jsx?$/.test(file) && productionFiles.has(file)),
);
const unchecked = [...productionFiles].filter((file) => !checkedFiles.has(file)).sort();

console.log(
  `Frontend type migration: ${checkedFiles.size} checked JS files, ${unchecked.length} unchecked ` +
    `(ceiling ${baseline.maxUncheckedProductionJs}).`,
);

if (unchecked.length > baseline.maxUncheckedProductionJs) {
  console.error("Unchecked production JavaScript increased. Add the new file to the checkJs boundary or lower the baseline.");
  process.exitCode = 1;
}
