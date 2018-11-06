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
from datetime import datetime

class URL(Enum):
    Official_news_url = "http://forums.maplestory2.nexon.net/categories/official-news"
    Event_news_url = "http://forums.maplestory2.nexon.net/categories/contests-and-events"
    Blog_news_url = "http://forums.maplestory2.nexon.net/categories/maple-2-team-blogs"

class News(commands.Cog):
    """Discord bot for MapletStory 2"""

    ###   VARIABLES ###
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subscriptions.json')
    subscription_timer = 900 # 900 seconds = 15 minutes

    #   START HERE
    def __init__(self, bot):
        print('News cog initializing...')
        self.bot = bot
        self.task = bot.loop.create_task(self._start_news_check_scheduler())

    async def _start_news_check_scheduler(self):
        while True:
            #   sleep until next task
            await asyncio.sleep(self.subscription_timer) #  900 = 15 minutes
            
            print('[TASK] Starting news check as of {}...'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            # your job code here
            await self._broadcast_latest_news()

            print('Running next task cycle in {} seconds...'.format(self.subscription_timer))
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
            await print('There are no subscribers! Doing nothing...')
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
        args = [(channel_id, news) for channel_id in channel_ids]
        tasks = itertools.starmap(self._publish_news_to_channel, args)
        await asyncio.gather(*tasks)

    async def _publish_news_to_channel(self, channel_id, news):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            await print('Unable to fetch channel id: {}!'.format(channel_id))
            return
        subscriptions_data = self._get_subscriptions_data()
        server = channel.guild
        channel_id = str(channel.id)
        server_id = str(server.id)

        latest_official_news = news['latest_official_news']
        latest_event_news = news['latest_event_news']
        latest_blog_news = news['latest_blog_news']
        
        #   check if this is the latest news for this channel
        if  subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_official_news'] != latest_official_news['id']:
            subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_official_news'] = latest_official_news['id']
            self._save_subscriptions_data(subscriptions_data)
            await self._say_news_on_channel(channel, latest_official_news['date_created'], latest_official_news['title'], latest_official_news['link'])
        else:
            print('Latest official news ({}) already posted in {}:{}, doing nothing...'.format(latest_official_news['title'], server.name, channel.name))

        if  subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_event_news'] != latest_event_news['id']:
            subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_event_news'] = latest_event_news['id']
            self._save_subscriptions_data(subscriptions_data)
            await self._say_news_on_channel(channel, latest_event_news['date_created'], latest_event_news['title'], latest_event_news['link'])
        else:
            print('Latest event news ({}) already posted in {}:{}, doing nothing...'.format(latest_event_news['title'], server.name, channel.name))

        if  subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_blog_news'] != latest_blog_news['id']:
            subscriptions_data['servers'][server_id]['channels'][channel_id]['latest_blog_news'] = latest_blog_news['id']
            self._save_subscriptions_data(subscriptions_data)
            await self._say_news_on_channel(channel, latest_blog_news['date_created'], latest_blog_news['title'], latest_blog_news['link'])
        else:
            print('Latest blog news ({}) already posted in {}:{}, doing nothing...'.format(latest_blog_news['title'], server.name, channel.name))

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

                #   append item to items list
                news_items.append(item)

            #   Return only the latest news
            latest_news = news_items[0]
            for item in news_items:
                #   parse datetime string to datetime before comparing
                item_date_created = dateutil.parser.parse(item['date_created'])
                latest_news_date_created = dateutil.parser.parse(latest_news['date_created'])
                if item_date_created > latest_news_date_created:
                    latest_news = item
            return latest_news

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
        #   else... add server and channel to database
        else:
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
    
    @news.command(aliases=["unsub"])
    async def unsubscribe(self, ctx: commands.Context):
        server = ctx.message.guild
        channel = ctx.message.channel
        server_id = str(server.id)
        channel_id = str(channel.id)
        # json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'subscriptions.json')

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
    
    