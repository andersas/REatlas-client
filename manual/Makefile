all:
	pdflatex manual.tex
	bibtex manual
	pdflatex manual.tex
	pdflatex manual.tex

clean:
	rm -f manual.aux manual.log manual.blg manual.toc manual.bbl *.cpt
	rm -f methods.log 
	
