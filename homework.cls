\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{homework}[2021/12/26 A Class for CMU 15-415 Homework]

\LoadClass{article}

\RequirePackage{enumitem}
\setlist[enumerate, 1]{label=(\alph*)}
\setlist[enumerate, 2]{label=\roman*.}

\RequirePackage{titlesec}
\titlelabel{Question \thesection: }
