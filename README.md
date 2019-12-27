UMAP  
====
[![Maintainability](https://api.codeclimate.com/v1/badges/7ea409c6588d420e4baa/maintainability)](https://codeclimate.com/github/New-Village/umap/maintainability)  
UMAP is an all-in-one solution for Japanese horse racing prediction. It is possible to manage that are collecting data, creates models, applies model, view predictions and these functions automation on Web UI.

## Requirement
* Docker 19.03.5
* docker-compose 1.25.0
* git

## Usage
1. Download & Start Umap Service
```bash
$ cd ~
$ git clone git@github.com:New-Village/umap.git
$ cd umap
$ sudo docker-compose -f "docker-compose.yml" up -d --build
```
2. Access http://{SERVER}:5000/race
