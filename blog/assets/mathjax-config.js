/* MathJax v3 configuration shared by all posts.
   Macros mirror common/tex/preamble.tex in the math repository. */

window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    tags: "none",
    macros: {
      Z: "\\mathbb{Z}",
      N: "\\mathbb{N}",
      Q: "\\mathbb{Q}",
      R: "\\mathbb{R}",
      F: "\\mathbb{F}",
      C: "\\mathbb{C}",
      lcm: "\\operatorname{lcm}",
      sgn: "\\operatorname{sgn}",
      dist: "\\operatorname{dist}",
      vol: "\\operatorname{vol}",
      spn: "\\operatorname{span}",
      norm: ["\\lVert #1\\rVert", 1],
      ip: ["\\langle #1,\\,#2\\rangle", 2]
    }
  },
  options: {
    ignoreHtmlClass: "no-mathjax",
    processHtmlClass: "math"
  },
  chtml: {
    scale: 1.02
  }
};
