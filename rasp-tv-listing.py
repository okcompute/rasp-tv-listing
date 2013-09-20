from dateutil import parser
import pygame
from rovi.tv_listings import TVListings
import ConfigParser
import calendar
from collections import namedtuple
import datetime
import platform
import time
from requests import ConnectionError

# Some objects to play with...
Channel = namedtuple('Channel', ['name', 'airings'])
Airing = namedtuple('Airing', ['title', 'time', 'duration'])
Position = namedtuple('Position', ['x', 'y'])
Size = namedtuple('Size', ['width', 'height'])


class Schedule(object):

    """ Manage Rovi api."""
    LISTING_UPDATE_TIME = 15 * 60
    WAIT_FOR_RETRY_AFTER_ERROR = 5  # check connection back every 5 seconds

    def __init__(self):
        config = ConfigParser.RawConfigParser()
        config.read('rasp-tv-listing.cfg')
        api_key = config.get('rasp-tv-listing', 'api_key')
        self.postal_code = config.get('rasp-tv-listing', 'postal_code')
        self.country_code = config.get('rasp-tv-listing', 'country_code')
        channels = config.get('rasp-tv-listing', 'channels').split(',')
        self.channels = [unicode(channel.strip()) for channel in channels]
        self.tv_listings = TVListings(api_key=api_key)
        self.update_time = 0
        self.error_time = 0
        self.source_ids = 0

    def _utc_to_local(self, t):
        """ Convert from utc time to local time. """
        secs = calendar.timegm(t)
        return time.localtime(secs)

    def _get_broadcast_service_id(self, postal_code, country_code):
        """ Return the service id for the first broadcast service found at the
        specified country and postal code. """
        services_response = self.tv_listings.services(
            postal_code=postal_code, country_code=country_code)
        services = services_response.get(
            'ServicesResult').get('Services').get('Service')
        broadcast_filter = lambda service: service.get('Type') == u'Broadcast'
        broadcast_services = filter(broadcast_filter, services)
        # pick the first broadcast service. No means to choose at this point.
        local_broadcast_service = broadcast_services[0]
        return local_broadcast_service.get('ServiceId')

    def _get_channels_source_ids(self, service_id, limit_channels=None):
        """ Return list of correspondings sources ids for a list of channels. If no
        channels are set, all source ids for the service are returned. """
        details = self.tv_listings.service_details(service_id=service_id)
        source_ids = []
        channels = details.get('ServiceDetailsResult').get(
            'ChannelLineup').get('Channels')
        for channel in channels:
            if channel.get('VirtualChannelNumber') in limit_channels:
                source_ids.append(channel.get('SourceId'))
        return source_ids

    def _get_channels_schedule(self, service_id, source_ids=None, duration=120):
        """ Return list of Channel instance for the provided sources_id on the service. """
        grid_schedule = self.tv_listings.grid_schedule(service_id=service_id,
                                                       duration=duration,
                                                       source_id=source_ids)
        grid_channels = grid_schedule.get(
            'GridScheduleResult').get('GridChannels')
        print "Channel counts: %d" % len(grid_channels)
        channels = []
        for grid_channel in grid_channels:
            print 80 * "-"
            print "Channel: " + grid_channel.get('DisplayName'), grid_channel.get('SourceLongName'), "(" + grid_channel.get('Channel') + ")"
            airings = []
            for airing in grid_channel.get('Airings'):
                airtime = parser.parse(airing.get('AiringTime'))
                local_airtime = self._utc_to_local(airtime.timetuple())
                formatted_airtime = time.strftime("%H:%M", local_airtime)
                print formatted_airtime + ": " + airing.get('Title'), "(%s minutes)" % airing.get('Duration')
                airings.append(Airing(title=airing.get('Title'),
                                      time=local_airtime,
                                      duration=int(airing.get('Duration'))))
            channels.append(Channel(name=grid_channel.get('DisplayName'),
                                    airings=airings))
        return channels

    def get_schedule(self):
        """ Return the schedule for channels set in rasp-tv.conf.

        Update TV listing from Rovi service every LISTING_UPDATE_TIME seconds

        """
        if self.error_time != 0:
            if time.time() - self.error_time > Schedule.WAIT_FOR_RETRY_AFTER_ERROR:
                self.error_time = 0
            else:
                raise Exception(self.error_messge)
        try:
            if not self.source_ids:
                self.service_id = self._get_broadcast_service_id(
                    self.postal_code,
                    self.country_code)
                self.source_ids = self._get_channels_source_ids(
                    self.service_id, self.channels)
            # Setup TVListing api
            # update every 15 minutes
            if time.time() - self.update_time > Schedule.LISTING_UPDATE_TIME:
                self.schedule = self._get_channels_schedule(
                    self.service_id, self.source_ids)
                self.network_error = False
                self.update_time = time.time()
            return self.schedule
        except ConnectionError:
            self.error_time = time.time()
            self.error_messge = "Network error. Verify your connection."
            raise Exception(self.error_messge)
        except ValueError:
            self.error_time = time.time()
            self.error_messge = "TV listing data unavailable at this moment."
            raise Exception(self.error_messge)


class Renderer(object):

    """ PyGame renderer for displaying the tv schedule. """

    # some constants
    SCREEN_SIZE = Size(1280, 720)
    LEFT_COLUMN = 150
    MIDDLE_COLUMN = LEFT_COLUMN + 200
    AIRING_VERTICAL_SPACING = 35
    CHANNEL_VERTICAL_SPACING = 60
    CHANNEL_POSITION = Position(LEFT_COLUMN, 65)
    AIRING_POSITION = Position(MIDDLE_COLUMN, 65)
    CLOCK_POSITION = Position(MIDDLE_COLUMN, 15)
    RED = pygame.Color(255, 12, 12)
    WHITE = pygame.Color(255, 255, 255)
    GREY = pygame.Color(160, 160, 160)

    def __init__(self):
        pygame.init()

        if platform.platform() is "armvv61":
            pygame.mouse.set_visible(False)
            self.screen = pygame.display.set_mode(
                Renderer.SCREEN_SIZE, pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(Renderer.SCREEN_SIZE)

    def _tick(self):
        """ One loop. """
        for event in pygame.event.get():  # User did something
            if event.type == pygame.QUIT:  # If user clicked close
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return False
        pygame.display.update()
        return True

    def tick(self, channels):
        """ One loop. """
        self._draw(channels)
        return self._tick()

    def tick_error(self, msg=None):
        """ One error loop. """
        self._draw_error(msg)
        return self._tick()

    def _draw(self, channels):
        """ Blit data onto PyGame's screen."""
        black = 0, 0, 0
        self.screen.fill(black)

        font = pygame.font.SysFont("freeserif", 28)

        # Draw time
        clock_surface = font.render(
            datetime.datetime.now().strftime("%H:%M"),
            True,
            pygame.Color(0, 255, 255))
        # center clock
        x = (Renderer.SCREEN_SIZE.width - clock_surface.get_width()) / 2
        self.screen.blit(clock_surface, (x, Renderer.CLOCK_POSITION.y))

        channel_count = 0
        y = Renderer.CHANNEL_POSITION.y
        for channel in channels:

            # Channel name
            airing_count = 0
            x = Renderer.CHANNEL_POSITION.x
            channel_name_surface = font.render(
                channel.name, True, Renderer.RED)
            self.screen.blit(channel_name_surface, (x, y))

            for airing in channel.airings:
                # Format airing text
                dt = datetime.datetime.fromtimestamp(time.mktime(airing.time))
                now = datetime.datetime.now()
                if now > dt and now < dt + datetime.timedelta(airing.duration):
                    color = Renderer.WHITE
                else:
                    color = Renderer.GREY
                formatted_airtime = time.strftime("%H:%M", airing.time)
                formatted_airtime = "%s - %s   (%s min)" % (
                    formatted_airtime, airing.title, airing.duration)
                airing_surface = font.render(formatted_airtime, True, color)
                x = Renderer.AIRING_POSITION.x
                self.screen.blit(airing_surface, (x, y))

                # No more than 3 airing per channel
                airing_count = airing_count + 1
                if airing_count >= 3:
                    break
                y = y + Renderer.AIRING_VERTICAL_SPACING

            # No more than 4 channels
            channel_count = channel_count + 1
            if channel_count >= 4:
                break
            y = y + Renderer.CHANNEL_VERTICAL_SPACING

    def _draw_error(self, msg):
        """ Blit error message onto PyGame's screen."""
        red = 128, 0, 0
        self.screen.fill(red)

        font = pygame.font.SysFont("freeserif", 28)

        # Draw time
        clock_surface = font.render(
            datetime.datetime.now().strftime("%H:%M"),
            True,
            pygame.Color(0, 255, 255))
        # center clock
        x = (Renderer.SCREEN_SIZE.width - clock_surface.get_width()) / 2
        self.screen.blit(clock_surface, (x, Renderer.CLOCK_POSITION.y))

        # Draw error message
        error_surface = font.render(msg,
                                    True,
                                    pygame.Color(255, 255, 255))
        # center message
        x = (Renderer.SCREEN_SIZE.width - error_surface.get_width()) / 2
        self.screen.blit(error_surface, (x, Renderer.CHANNEL_POSITION.y))

if __name__ == "__main__":

    # Rovi Tv listing
    schedule = Schedule()
    # Pygame renderer
    renderer = Renderer()

    # Loop forever.
    running = True
    while running:
        try:
            running = renderer.tick(schedule.get_schedule())
        except Exception as e:
            running = renderer.tick_error(e.message)
