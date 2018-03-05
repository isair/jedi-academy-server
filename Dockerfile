FROM centos
MAINTAINER Baris Sencan <baris.sncn@gmail.com>

# Expose a range of possible Jedi Academy ports.
EXPOSE 29060-29062/udp 29070-29081/udp

# Install dependencies.
RUN yum install -y glibc.i686

# Copy server files.
COPY server/libcxa.so.1 /usr/lib/libcxa.so.1
COPY server/linuxjampded /opt/ja-server/linuxjampded
COPY server/jampgamei386.so /opt/ja-server/jampgamei386.so
COPY server/start.sh /opt/ja-server/start.sh
COPY server/run-rtvrtm.py opt/yoda/run-rtvrtm.py
COPY server/yoda /opt/yoda/yoda

# Mount game data volume.
VOLUME /jedi-academy

# Set the working directory to where the Jedi Academy data files will be
# mounted at, so that linuxjampded finds them.
WORKDIR /jedi-academy

# Start the server.
CMD ["/opt/ja-server/start.sh"]
