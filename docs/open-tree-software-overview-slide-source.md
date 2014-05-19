# Open Tree of Life Software Goals
1. produce a comprehensive taxonomy
1. enable curation of phylogenies
1. create a supertree - the "synthetic tree"
1. enable users to browse the synthetic tree and "graph of life"


---
# Phylografter
* provided study curation user interface
* primary study database 

---
Phylografter Sortable, Searchable Study Dashboard:
<div id="container">
 <img alt="Phylografter study list" src="images/phylografter-study-list.png" width="800" height="600" />
</div>

---
Phylografter OTU Mapping:
<div id="container">
 <img alt="Phylografter OTU Mapping" src="images/phylografter-otu-mapping.png" />
</div>

---
Phylografter Tree Editing:
<div id="container">
 <img alt="Phylografter Tree Editing" src="images/phylografter-tree.png"  />
</div>

---
Synthetic tree browsing:
<div id="container">
 <img alt="Browsing the synthetic tree" src="images/synth-tree-browse-Parulidae.png" width="800" height="600" />
</div>

---
Synthetic tree commenting:
<div id="container">
 <img alt="Browsing the synthetic tree" src="images/synth-tree-comment.png" width="800" height="600" />
</div>

---
<div id="container">
 <img alt="2013 Architecture" src="images/architecture-user-2013.svg" width="800" height="600" />
</div>

---
<div id="container">
 <img alt="2013 Architecture" src="images/architecture-2013.svg" width="800" height="600" />
</div>

---
# "smasher"
* Command-line tool written/run by Jonathan Rees
* Rule-based combination of:
    * taxonomies from NCBI, GBIF, IRMNG, Index Fungorum
    * tips from SILVA
    * arbitrary taxonomic edits by curators
* Produces a versioned Open Tree Taxonomy (OTT)

---
# taxomachine
* Takes OTT as input
* Provides string-to-OTT ID services and other taxonomic APIs
* neo4j backend
* written by Cody Hinchliff and others in Smith lab.

---
<div id="container">
 <img alt="2013 Architecture" src="images/architecture-2013.svg" width="800" height="600" />
</div>

---
# Phylografter
* Front-end for curation of phylogenetic estimates
* Started by Ree lab before the Open Tree project, but significantly extended in years 1 and 2.
* imports OTT and trees into a relational database
* provides views on the trees, OTU mapping, and some conflict summaries
* can export studies to NexSON

---
# Bitbucket NexSON repo
* <code>git</code> (version control system) repository of phylografter exports
* a script can pull down the newly-updated studies from phylografter.
* used as the input for treemachine
* gives us a very loose dependence between phylografter and treemachine

---
# treemachine
* reads OTT as a tree and trees from NexSON
* reads a list of study ranking to be used when resolving conflicts.
* creates a "graph of life" of all of the input trees in a neo4j database
* implements [a novel supertree algorithm](http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1003223) for selecting which branches should go in the "synthetic tree of life"
* treemachine "plugin" used to provide web services to explore the tree.

---
# synthetic tree browser
* JavaScript front end (runs in the user's web-browser) for the synthetic tree
* uses taxomachine and treemachine services
* enables
    * navigation of the tree
    * commenting
    * searching for taxa in the tree

---
<div id="container">
 <img alt="2013 Architecture" src="images/architecture-user-2013.svg" width="800" height="600" />
</div>

---
<div id="container">
 <img alt="2013 Architecture" src="images/architecture-2013.svg" width="800" height="600" />
</div>



