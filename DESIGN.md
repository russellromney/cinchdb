# CinchDB

CinchDB has five components: 
1. a Python SDK where the core functionality lives, that can either operate locally or use a remote connection. This also manages simple UUID4 API keys that have read/write permissions for all branches or a specific branch
2. a FastAPI API that uses the SDK to implement core functionality in a remote server
3. a Typescript SDK that can only call the API, designed for Node backends or Javascript webapps
4. a Python Typer CLI that simply calls the Python SDK to do all its work either locally or to call the API
5. A docs server that unifies all docs into one place including tutorials, SDK, CLI, API, etc. 

Core functionality: 
* CinchDB uses SQLite in WAL mode with autocheckpoint turned off, in NORMAL mode
* Each project exists in a local folder called .cinchdb
* Inside .cinchdb is a config.toml file that lists the active database and branch, as well as any API keys
* A project can have multiple databases
* A database can have multiple branches
* Each branch can have multiple tenants
* Branches and tenants are implied from the directory structure, so we don’t ever have differences between meta state and actual state
* A new branch is created by copying the directory of another branch - all tenants are automatically copied, always
* Users can add tables and columns within the branch. They cannot do anything else.
* Each table automatically has a UUID4 "id" field and created_at/updated_at timestamps to the millisecond. That means these names are protected. 
* Users can create "Models" as well that function like normal tables, but are created with a SQL statement. These are also tracked as changes and saved as views within SQLite
* Branches track the current structure in a JSON file in the branch directory. 
* Within each database, changes to a given branch are tracked inside the branch directory in a simple JSON file. 
* You can merge changes from one branch into another. You cannot make changes directly to the main branch, you can only merge them. a change can only be merged if the branch possesses all existing changes in the previous branch. This limits the functionality but forces safety
* All structure changes are always applied to each tenant in the branch. There is no other option. 
* In general, if a tenant isn't specified, then CinchDB assumes you are using the main tenant

Commands
* Project
    * Init - creates a .cinchdb directory with a main database, branch, and tenant
* db 
    * List - list all databases in the project, which is the .cinchdb directory unless otherwise specified
    * Create - make a new database in the project
    * Delete - delete an existing database in the project
    * Info  - show the branches in the project 
    * Tenant
        * List - list the tenants in the branch
        * Create - create a new tenant in the branch
        * Delete - delete a tenant in the branch
        * Rename - change the tenant’s name in the branch
    * Copy - create a new tenant in the branch from another tenant
* Branch
    * List - list the branches in the active database
    * Create - create a new branch in the active database
    * Delete - delete a branch from the active database
    * Switch - change the active branch in the config
    * Merge  - from a source branch to a target branch
* Table
    * List - list the tables in the branch
    * Create - create a new table in the branch
    * Copy - create a new table as a copy of another table
    * Delete - delete a table from the branch
    * Info - describe the columns and contents of the table
* Column (in Table)
    * List - list the column names and types of the table
    * Create - create a new column in a table
    * Delete - delete a column from a table
    * Rename - rename a column in a table
    * Info - describe a column
* View
    * List - list the saved views
    * Create - create a new view with a SQL statement
    * Rename - change the name of a saved view
    * Delete - delete a saved view
    * Info - describe a specific view (show the SQL)
* Query - get the results of a SQL SELECT statement from the database
* Serve
* Codegen
    * Languages - list the available languages to generate (Python and Typescript)
    * Generate - create a folder of models that match your Tables/Views and can be used to fetch and update CinchDB tables
