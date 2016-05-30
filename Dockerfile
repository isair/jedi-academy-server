FROM ubuntu

LABEL maintainer="baris.sncn@gmail.com"

# Expose a range of possible Jedi Academy ports.
EXPOSE 29060-29062/udp 29070-29081/udp

# Install dependencies.
RUN apt-get update && apt-get -y install lib32z1 lib32stdc++6 ca-certificates python

# Copy server files.
RUN mkdir /opt/ja-server
COPY server/openjkded.i386 /opt/ja-server/openjkded.i386
COPY server/start.sh /opt/ja-server/start.sh
COPY server/run-rtvrtm.py opt/yoda/run-rtvrtm.py
COPY server/yoda /opt/yoda/yoda

# Mount game data volume and start the server.
VOLUME /jedi-academy
CMD ["/opt/ja-server/start.sh"]
