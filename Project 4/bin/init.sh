# create database via csv files
sqlite-utils insert ../var/users.db users --csv ../share/users.csv --detect-types --pk=user_id
sqlite-utils insert ../var/users.db follows --csv ../share/follows.csv --detect-types --pk=id
sqlite-utils insert ../var/posts.db posts --csv ../share/posts.csv --detect-types --pk=id

# add foreign keys (optional)
sqlite-utils add-foreign-key ../var/users.db follows user_id users user_id
sqlite-utils add-foreign-key ../var/users.db follows following_id users user_id
