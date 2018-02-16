import httplib
import urllib


class PushNotificationManager():

    @staticmethod
    def send(message):
        assert isinstance(message, str)
        conn = httplib.HTTPSConnection("api.pushover.net:443")
        # TODO: Get keys from a configuration file.
        conn.request("POST", "/1/messages.json",
                     urllib.urlencode({
                         "token": "apegq7wck35j2zrijg6vv9furaj2qr",
                         "user": "u693a8wszdyjvbd5s5td5qxe6gvrih",
                         "message": message,
                     }), {"Content-type": "application/x-www-form-urlencoded"})
        conn.getresponse()
