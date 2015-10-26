#ifndef MEASURE_HPP
#define	MEASURE_HPP
#include <string>
#include "Graph.hpp"
#include "utils.hpp"
#include "Alignment.hpp"

class Measure {
public:

    Measure(Graph* G1, Graph* G2, string name);
    virtual ~Measure();
    virtual double eval(const Alignment& A) =0;
    string getName();
    virtual bool isLocal();

protected:
	Graph* G1;
	Graph* G2;
	
private:
	string name;

};

#endif
