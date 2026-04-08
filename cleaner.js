function main(config) {
  function clean(obj) {
    if (typeof obj === "string") {
      // Remove all invalid control chars except \n \r \t
      return obj.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, "");
    } else if (Array.isArray(obj)) {
      return obj.map(clean);
    } else if (typeof obj === "object" && obj !== null) {
      for (let key in obj) {
        obj[key] = clean(obj[key]);
      }
    }
    return obj;
  }

  return clean(config);
}
