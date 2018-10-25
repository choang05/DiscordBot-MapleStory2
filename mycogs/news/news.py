from redbot.core import commands, checks
from bs4 import BeautifulSoup
import requests
import dateutil.parser
from enum import Enum
import time
import json
import os
import asyncio
import itertools

class URL(Enum):
    Official_news_url = "http://forums.maplestory2.nexon.net/categories/official-news"
    Event_news_url = "http://forums.maplestory2.nexon.net/categories/contests-and-events"
    Blog_news_url = "http://forums.maplestory2.nexon.net/categories/maple-2-team-blogs"

class News(commands.Cog):
    """Discord bot for MapletStory 2"""

    ###   VARIABLES ###
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subscriptions.json')

    #   START HERE
    def __init__(self, bot):
        print('News bot initializing...')
        self.bot = bot
        self.task = bot.loop.create_task(self._start_news_check_scheduler())
        self._start_news_check_scheduler()
        self._broadcast_latest_news()

    async def _start_news_check_scheduler(self):
        while True:
            #   sleep until next task
            await asyncio.sleep(900) #  900 = 15 minutes
            
            print('Starting scheduled task: news check...')
            
            # your job code here
            await self._broadcast_latest_news()

            # return

    async def _broadcast_latest_news(self):
        """
            Returns the single latest news given a array of news dictionary   
        """

        #   check if there are any channels to subscribe to
        data = self._get_subscriptions_data()
        has_subscribers = False
        for server_id in data['servers'].keys():
            if data['servers'][server_id]['channels']:
                has_subscribers = True
                break
        if not has_subscribers:
            print('There are no subscribers! Doing nothing...')
            return

        print('There are subscribers, fetching latest news and publishing to subscribers...')
        latest_official_news = self._get_latest_news(URL.Official_news_url.value)
        latest_event_news = self._get_latest_news(URL.Event_news_url.value)
        latest_blog_news = self._get_latest_news(URL.Blog_news_url.value)
        news = {
            "latest_official_news": latest_official_news,
            "latest_event_news": latest_event_news,
            "latest_blog_news": latest_blog_news,
        }

        #   get list of channel ids to publish to
        channel_ids = []
        for server_id, server in data['servers'].items():
            for channel_id in server['channels'].keys():
                channel_ids.append(int(channel_id))

        #   perform async tasks to broadcast to each channel id
        args = [(channel_id, news, data) for channel_id in channel_ids]
        tasks = itertools.starmap(self._publish_news_to_channel, args)
        await asyncio.gather(*tasks)

    async def _publish_news_to_channel(self, channel_id, news, subscriptions_data):
        channel = self.bot.get_channel(channel_id)
        server = channel.guild
        channel_id = str(channel.id)
        server_id = str(server.id)

        latest_official_news = news['latest_official_news']
        latest_event_news = news['latest_event_news']
        latest_blog_news = news['latest_blog_news']
        
        #   check if this is the latest news for this channel. Check if latest_news is empty string
        if not subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_official_news']:
            subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_official_news'] = latest_official_news['id']
            self._save_subscriptions_data(subscriptions_data)
            await self._say_news_on_channel(channel, latest_official_news['date_created'], latest_official_news['title'], latest_official_news['link'])
        else:
            print('Latest official news already posted in {}:{}, doing nothing...'.format(server.name, channel.name))

        if not subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_event_news']:
            subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_event_news'] = latest_event_news['id']
            self._save_subscriptions_data(subscriptions_data)
            await self._say_news_on_channel(channel, latest_event_news['date_created'], latest_event_news['title'], latest_event_news['link'])
        else:
            print('Latest event news already posted in {}:{}, doing nothing...'.format(server.name, channel.name))

        if not subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_blog_news']:
            subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_blog_news'] = latest_blog_news['id']
            self._save_subscriptions_data(subscriptions_data)
            await self._say_news_on_channel(channel, latest_blog_news['date_created'], latest_blog_news['title'], latest_blog_news['link'])
        else:
            print('Latest blog news already posted in {}:{}, doing nothing...'.format(server.name, channel.name))

    async def _say_news_on_channel(self, channel, date, title, link):
        #   message builder
        msg = '{:%B %d, %Y}'.format(dateutil.parser.parse(date))
        msg += "\n"
        msg += title
        msg += "\n"
        msg += link
        await channel.send(msg)

    def _get_latest_news(self, url):
        """
            Returns the single latest news given a array of news dictionary   
        """
        #   if status code is successful...
        response = requests.get(url)
        if response.status_code == 200:
            news_items = []
            #   initialize BS4 object
            soup = BeautifulSoup(response.content, 'html.parser')
            # for row in soup.findAll('table')[0].tbody.findAll('tr'):
            for row in soup.select('tr'):
                #   Fetch and extract data
                discussion_id = row.get('id')
                #   Skip any rows that lack a title
                if discussion_id == None: continue
                    
                title = row.find('a', attrs={'class': 'Title'})
                if  title == None: raise Exception ('Title could not be found!')
                link = row.find('a', attrs={'class': 'Title'})
                if  link == None: raise Exception ('Link could not be found!')
                date_created = row.find('time')
                if  date_created == None: raise Exception ('date_created could not be found!')

                #   Clean up data
                title = title.text  # find text in title selector
                # get the link within selector AND add 1st url parameter to link
                link = link.get('href') + '/p1'
                # Get the datetime within the selector and convert to datetime obj
                #date_created = dateutil.parser.parse(date_created['datetime'])

                #   Create dictionary item
                item = {
                    'id': discussion_id,
                    'title': title,
                    'link': link,
                    'date_created': date_created['datetime']
                }

                #   TODO return the latest, maybe improve code in the future
                return item

                #   append item to items list
                news_items.append(item)

            #   from news items, only get the latest news
            # return news_items[0]

    def _save_subscriptions_data(self, data):
        #   open json file and overwrite data then close
        json_file = open(self.json_path, 'w')
        json.dump(data, json_file)
        json_file.close()

    def _get_subscriptions_data(self):
        #   open json file and load data then close
        json_file = open(self.json_path, 'r')
        data = json.load(json_file)
        json_file.close()
        return data

    @commands.group(autohelp=True)
    async def news(self, ctx: commands.Context):
        """Check news by using the commands listed below
        """ 
        pass

    # @commands.command()
    # async def test1(self, ctx: commands.Context):
    #     msg = self._get_latest_news(URL.Official_news_url.value)['date_created']
    #     await ctx.send(msg)

    @news.command(aliases=["sub"])
    async def subscribe(self, ctx: commands.Context):
        server = ctx.message.guild
        channel = ctx.message.channel
        server_id = str(server.id)
        channel_id = str(channel.id)

        data = self._get_subscriptions_data()

        #   check if server exists...
        if server_id in data['servers']:
            #   check if channel is already subscribed...
            if channel_id in data['servers'][server_id]['channels']:
                await ctx.send('This channel is already subscribed!')
                return
            #   else... add channel to database
            else:
                print('{} channel not in database... adding to database...'.format(channel.name))
                #   create structure
                channel_data = {
                    'name':channel.name,
                    'latest_official_news': '',
                    'latest_event_news': '',
                    'latest_blog_news': ''
                }
                #   create data in json structure
                data['servers'][server_id]['channels'][channel_id] = channel_data

                self._save_subscriptions_data(data)

                await ctx.send('I will now post news in this channel!')
                return
        #   else... add server and channel to database
        else:
            return
            print('{} server not in database... adding to database...'.format(server.name))
            data['servers'][server_id] = {
                "name": server.name,
                "channels": {
                    channel_id: {
                        "name": channel.name,
                        "latest_official_news": '',
                        "latest_event_news": '',
                        "latest_blog_news": ''
                    }
                }
            }
            self._save_subscriptions_data(data)
            await ctx.send('I will now post news in this channel!')
            return
    
    @news.command(aliases=["unsub"])
    async def unsubscribe(self, ctx: commands.Context):
        server = ctx.message.guild
        channel = ctx.message.channel
        server_id = str(server.id)
        channel_id = str(channel.id)
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subscriptions.json')

        data = self._get_subscriptions_data()

        #   check if server exists...
        if server_id in data['servers']:
            #   check if channel is already subscribed...
            if channel_id in data['servers'][server_id]['channels']:
                #   delete the channel key
                del data['servers'][server_id]['channels'][channel_id]
                self._save_subscriptions_data(data)
                await ctx.send('This channel has been unsubscribed!')
                return
            else:
                await ctx.send('This channel was never subscribed!')
        else:
            await ctx.send('This channel was never subscribed!')

    @news.command(name='latestofficial')
    async def post_latest_official(self, ctx: commands.Context):
        latest_news = self._get_latest_news(URL.Official_news_url.value)
        await self._say_news_on_channel(ctx.channel, latest_news['date_created'], latest_news['title'], latest_news['link'])

    @news.command(name='latestevent')
    async def post_latest_event(self, ctx: commands.Context):
        latest_news = self._get_latest_news(URL.Event_news_url.value)
        await self._say_news_on_channel(ctx.channel, latest_news['date_created'], latest_news['title'], latest_news['link'])

    @news.command(name='latestblog')
    async def post_latest_blog(self, ctx: commands.Context):
        latest_news = self._get_latest_news(URL.Blog_news_url.value)
        await self._say_news_on_channel(ctx.channel, latest_news['date_created'], latest_news['title'], latest_news['link'])
    
    