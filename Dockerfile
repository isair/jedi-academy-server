FROM centos
MAINTAINER Baris Sencan <baris.sncn@gmail.com>

# Expose a range of possible Jedi Academy ports.
EXPOSE 29060-29062/udp 29070-29081/udp

# Install dependencies.
RUN yum install -y glibc.i686 wget

# Download and extract OpenJK.
RUN wget https://builds.openjk.org/openjk-2016-04-13-0bbbccf2-linux-64.tar.gz -O /tmp/openjk.tar.gz
RUN mkdir /tmp/openjk
RUN tar zxvf /tmp/openjk.tar.gz -C /tmp/openjk

# Copy server files.
RUN mkdir /opt/ja-server
RUN cp -r /tmp/openjk/install/JediAcademy/* /opt/ja-server
COPY server/start.sh /opt/ja-server/start.sh
COPY server/rtvrtm.py /opt/rtvrtm/rtvrtm.py

# Clean up.
RUN rm /tmp/openjk.tar.gz
RUN rm -rf /tmp/openjk

# Mount game data volume and start the server.
VOLUME /jedi-academy
CMD ["/opt/ja-server/start.sh"]
