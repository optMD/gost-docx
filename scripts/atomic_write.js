const fs = require("fs");
const path = require("path");

function atomicWrite(destination, contents) {
  const target = fs.existsSync(destination) ? fs.realpathSync(destination) : path.resolve(destination);
  const directory = fs.mkdtempSync(path.join(path.dirname(target), ".gost-build-"));
  const temporary = path.join(directory, "output.docx");
  try {
    fs.writeFileSync(temporary, contents, { flag: "wx" });
    fs.renameSync(temporary, target);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
    fs.rmdirSync(directory);
  }
}

module.exports = { atomicWrite };
