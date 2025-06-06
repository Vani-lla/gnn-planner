# School Timetabling with Graph Neural Networks

TimetableGNN is a research-driven project that explores how Graph Neural Networks (GNNs) can be applied to the School Timetabling Problem.
By modeling constraints (legal constraints, what lessons can happen in parrarel...) and objectives (minimization of the amout of paid teacher hours)
the model can iteratively generate feasible and optimized timetables.

## Key Features
- Graph-based modeling of constraints
- GNN scheduling prediction using Pytorch Geometric
- Customizable objective function

## Model architecture
- **Nodes**: Lessons that are required, eg.:
    - Math teached by X with class IA
    - PE teached by Y for class IA (males)
    - PE teached by Z for class IA (females)
- **Edges**: Relation between lessons, I implemented 4 types of connections:
    - (Conflicting) Lessons with the same teacher
    - (Conflicting) Lessons with the same class
    - (Compatible ) Lessons that can happen at the same time in the class, eg. PE for guys and girls
    - (Compatible ) Lessons that can happen at the same time with many classes, eg. French for IA, IB & IC
- **Graph Input**: Lessons embeddings, which are vectors of features:
    - How many more lessons does a class need to have
    - Is the prievous lessons a lesson of the same type?
    - ...
- **Output**: NxM matrix, where:
    - N is the number of lesson
    - M is the number of classes 
    - Each cell represents the predicted probability of assigning a lesson to a specific time slot

## Future work
As this is my bachelor's thesis in engineering, the final goal is to build a full-stack application featuring:
- Django for backend
- React/Angular for frontend
- Pytorch Geometric/Cplex for model calculation

The main goal of this application is to help school staff save time when creating timetables by clearly highlighting lesson conflicts and scheduling constraints. Instead of manually identifying issues, staff can easily spot and resolve conflicts with the system’s assistance.

What makes this approach unique is the use of Graph Neural Networks. Rather than automatically generating a complete plan (as traditional solvers like CPLEX do), our model suggests feasible scheduling options. This gives staff more control and flexibility—they can review, accept, or modify GNN-generated suggestions as they build the plan.
