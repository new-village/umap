db.createUser(
    {
        user: "admin",
        pwd: "UMap2020!",
        roles: [
            {
                role: "readWrite",
                db: "umap"
            }
        ]
    }
);