# Tribes Python server

## Intro
This is a reference implementation of the Tribes protocol. This server also has a web dashboard where server admins can add, block or message people who are members of the server. You can read more about the Tribes protocol and how it works at www.tribes.ltd

## Prerequistes
You will need a version of Python that is either above or at 3.10. You will also need to install uv, a Python development tool and package manager. 

The database used for this reference implementation is the Redisstack. This is the version of Redis that has the JSON extensions installed and running. You can use the Docker image RedisStack[(https://hub.docker.com/r/redis/redis-stack-server)] as starting point. 

