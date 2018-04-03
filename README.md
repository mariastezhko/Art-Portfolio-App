# Art Portfolio (Item Catalog Application Project for the Udacity Full Stack Nanodegree Course)

- - - -

![alt map](https://raw.githubusercontent.com/mariastezhko/Art-Portfolio-App/master/static/img/artportfolio.png)

## Description

`Art Portfolio` is a RESTful web application that provides a list of items within a variety of categories. `Art Portfolio` utilizes the Python framework Flask along with third-party OAuth authentication. Registered users have the ability to post, edit and delete their own items.

Key features of `Art Portfolio` include:

- Third-party OAuth authentication (Google, Facebook)
- Mapping HTTP methods to CRUD (create, read, update and delete) operations
- Considering authorization status prior to execution of CRUD operations
- CRUD functionality for image handling
- Responsive design
- JSON endpoints

`Art Portfolio` application features watercolor paintings by Maria Stezhko.


## Requirements

 - [Python](https://www.python.org/)
 - [Vagrant](https://www.vagrantup.com/)
 - [VirtualBox Virtual Machine](https://www.virtualbox.org/)


## Installation

 1. [Download VirtualBox](https://www.virtualbox.org/). Install the package.
 2. [Download Vagrant](https://www.vagrantup.com/). Install the package.
 3. [Download the Virtual Machine configuration](https://github.com/udacity/fullstack-nanodegree-vm)


## Usage Instructions

#### Starting the virtual machine

From the terminal, inside the **vagrant** subdirectory, run the command
```
$ vagrant up
```
Log into the virtual machine by running the command
```
$ vagrant ssh
```
#### Setting up the database

`Art Portfolio` application comes with already populated database artportfolio.db

To set up an empty database artportfolio.db, inside the /vagrant/artportfolio directory, run the command
```
$ python database_setup.py
```
#### Running the program

From the terminal, inside the /vagrant/artportfolio directory, run the command
```
$ python artportfolio.py
```
Access the application by visiting http://localhost:8000 locally.


## JSON endpoints

/artportfolio.json - Displays the art portfolio, including themes and paintings.

/themes/JSON - Displays all themes

/themes/<path:theme_name>/paintings/JSON - Displays paintings for a specific theme

/themes/<path:theme_name>/paintings/<path:paintings_name>/JSON - Displays a specific painting.
