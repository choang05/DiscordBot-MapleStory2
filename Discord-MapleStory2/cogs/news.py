import dateutil.parser
import datetime
import requests
import asyncio
import logging
from bs4 import BeautifulSoup
# import scrapy
# from scrapy.crawler import CrawlerProcess
import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import fileIO
from __main__ import send_cmd_help

log = logging.getLogger("red.news")
log.setLevel(logging.INFO)

global_official_news_url = 'http://forums.maplestory2.nexon.net/categories/official-news'
global_events_news_url = 'http://forums.maplestory2.nexon.net/categories/contests-and-events'
blogs_news_url = 'http://forums.maplestory2.nexon.net/categories/maple-2-team-blogs'

blog_database_path = 'data/news/blogs.json'

class News:
    """MapleStory 2 bot"""

    global global_official_news_url
    global global_events_news_url
    global blogs_news_url
    global blog_database_path

    @commands.group(pass_context=True, name="news")
    async def news(self, ctx):
        """Check news by using the commands listed below
        """ 

        #   Add "typing... " status
        await self.bot.send_typing(ctx.message.channel)

        if ctx.invoked_subcommand is None:
            # await self.bot.say(ctx.message.author.mention)
            await send_cmd_help(ctx)

    @news.command(name="official", pass_context=True)
    async def latest_official_news(self, ctx):
        """Get the latest news!"""

        #   Add "typing... " status
        await self.bot.send_typing(ctx.message.channel)

        #   if status code is successful...
        response = requests.get(global_official_news_url)
        if response.status_code == 200:
            log.info('Page request success')

            news = self._get_news(global_official_news_url)
            latest_official_news = self._get_latest_news(news)

            #message = self.bot.guilds.get("433766043098415127").channels.get(435539078637682688);
            # message = self.bot.server
            # print(message)
            #   msg builder
            msg = '{:%B %d, %Y}'.format(dateutil.parser.parse(latest_official_news['date_created']))
            msg += "\n"
            msg += latest_official_news['title']
            msg += "\n"
            msg += latest_official_news['link']

            log.info('News has been posted.')
            await self.bot.say(msg)
        else:
            log.info('Page request failed.')
            await self.bot.say("Sorry! I can't seem to get any news right now.")    

    @news.command(name="check_official", pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def check_latest_official(self, ctx):
        """Check the latest official news"""
        #   if status code is successful...
        response = requests.get(global_official_news_url)
        if response.status_code == 200:
            log.info('Page request success')

            news = self._get_news(response)
            latest_official_news = self._get_latest_news(news)

            # variables
            channel = ctx.message.channel
            server = ctx.message.server

            #   check if messsage exists in the data
            is_news_posted_already = False
            latest_official_news_in_database = fileIO('data/news/official.json', 'load')
            for item in latest_official_news_in_database:
                #   if there exists a server id and channel id in the database...
                if item['server_id'] == server.id and item['channel_id'] == channel.id:
                    #   if the database id matches the latest checked news id...
                    if item['latest_news']['id'] == latest_official_news['id']:
                        is_news_posted_already = True

            #   if there was the sames news already in the database, do nothing
            if is_news_posted_already == True:
                log.info('Official news has already been posted in channel "{}" in server "{}"! Doing nothing.'.format(channel.name, server.name))
                return
            #   else the latest news has not been posted yet...
            else:
                #   Delete previous posted news?


                #   create and save new news to database
                new_news = {
                    'server_name': server.name,
                    'server_id': server.id,
                    'channel_id': channel.id,
                    'channel_name': channel.name,
                    'latest_news': latest_official_news
                }
                latest_official_news_in_database.append(new_news)
                fileIO('data/news/official.json', 'save', latest_official_news_in_database)
                log.info('New news has been added to database.')


                #   Add "typing... " status
                await self.bot.send_typing(ctx.message.channel)

                #   msg builder
                msg = '{:%B %d, %Y}'.format(dateutil.parser.parse(latest_official_news['date_created']))
                msg += "\n"
                msg += latest_official_news['title']
                msg += "\n"
                msg += latest_official_news['link']

                log.info('New official news has been posted in channel "{}" in server "{}".'.format(
                    channel.name, server.name))
                await self.bot.say(msg)
                return
    
    @news.command(name="check_blogs", pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def check_latest_blogs(self, ctx):
        """Check the latest blogs news"""
        #   if status code is successful...
        response = requests.get(blogs_news_url)
        if response.status_code == 200:
            log.info('Page request success')

            news = self._get_news(response)
            latest_news = self._get_latest_news(news)

            # variables
            channel = ctx.message.channel
            server = ctx.message.server

            #   check if messsage exists in the data
            is_news_posted_already = False
            latest_news_in_database = fileIO(blog_database_path, 'load')
            for item in latest_news_in_database:
                #   if there exists a server id and channel id in the database...
                if item['server_id'] == server.id and item['channel_id'] == channel.id:
                    #   if the database id matches the latest checked news id...
                    if item['latest_news']['id'] == latest_news['id']:
                        is_news_posted_already = True

            #   if there was the sames news already in the database, do nothing
            if is_news_posted_already == True:
                log.info('Blog news has already been posted in channel "{}" in server "{}"! Doing nothing.'.format(channel.name, server.name))
                return
            #   else the latest news has not been posted yet...
            else:
                #   Delete previous posted news?

                #   create and save new news to database
                new_news = {
                    'server_name': server.name,
                    'server_id': server.id,
                    'channel_id': channel.id,
                    'channel_name': channel.name,
                    'latest_news': latest_news
                }
                latest_news_in_database.append(new_news)
                fileIO(blog_database_path, 'save',
                       latest_news_in_database)
                log.info('New blog news has been added to database.')

                #   Add "typing... " status
                await self.bot.send_typing(ctx.message.channel)

                #   msg builder
                msg = '{:%B %d, %Y}'.format(dateutil.parser.parse(
                    latest_news['date_created']))
                msg += "\n"
                msg += latest_news['title']
                msg += "\n"
                msg += latest_news['link']

                log.info('New blog news has been posted in channel "{}" in server "{}".'.format(
                    channel.name, server.name))
                await self.bot.say(msg)
                return

    @news.command(name="check_events", pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def check_latest_events(self, ctx):
        """Check the latest event news"""
        #   if status code is successful...
        response = requests.get(global_events_news_url)
        if response.status_code == 200:
            log.info('Page request success')

            news = self._get_news(response)
            latest_event_news = self._get_latest_news(news)

            # variables
            channel = ctx.message.channel
            server = ctx.message.server

            #   check if messsage exists in the data
            is_news_posted_already = False
            latest_event_news_in_database = fileIO('data/news/events.json', 'load')
            for item in latest_event_news_in_database:
                #   if there exists a server id and channel id in the database...
                if item['server_id'] == server.id and item['channel_id'] == channel.id:
                    #   if the database id matches the latest checked news id...
                    if item['latest_news']['id'] == latest_event_news['id']:
                        is_news_posted_already = True

            #   if there was the sames news already in the database, do nothing
            if is_news_posted_already == True:
                log.info('Event news has already been posted in channel "{}" in server "{}"! Doing nothing.'.format(channel.name, server.name))
                return
            #   else the latest news has not been posted yet...
            else:
                #   create and save new news to database
                new_news = {
                    'server_name': server.name,
                    'server_id': server.id,
                    'channel_id': channel.id,
                    'channel_name': channel.name,
                    'latest_news': latest_event_news
                }
                latest_event_news_in_database.append(new_news)
                fileIO('data/news/events.json', 'save', latest_event_news_in_database)
                log.info('New event news has been added to database.')


                #   Add "typing... " status
                await self.bot.send_typing(ctx.message.channel)

                #   msg builder
                msg = '{:%B %d, %Y}'.format(dateutil.parser.parse(latest_event_news['date_created']))
                msg += "\n"
                msg += latest_event_news['title']
                msg += "\n"
                msg += latest_event_news['link']

                log.info('New event news has been posted in channel "{}" in server "{}".'.format(channel.name, server.name))
                await self.bot.say(msg)
                return

    # @commands.command(pass_context=True)
    # async def load_news(self, data):
    #     items = fileIO('data/news/data.json', 'load')
    #     for data in items:
    #         print(data)
    #         if data['server_id'] == 5555555555:
    #             print("found!")
    #     log.info('loaded news')


    '''
        Returns the array of dictionary news after web extraction
    '''

    def _get_news(self, page):
        items = []

        #   initialize BS4 objs
        soup = BeautifulSoup(page.content, 'html.parser')

        # for row in soup.findAll('table')[0].tbody.findAll('tr'):
        for row in soup.select('tr'):
            #   Fetch and extract data
            discussion_id = row.get('id')
            title = row.find('a', attrs={'class': 'Title'})
            link = row.find('a', attrs={'class': 'Title'})
            date_created = row.find('time')
            #   Skip any rows that lack a title
            if discussion_id == None:
                continue

            #   Clean up data
            title = title.text  # find text in title selector
            # get the link within selector AND add 1st page parameter to link
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
            items.append(item)

        return items

    '''
        Returns the single latest news given a array of news dictionary   
    '''

    def _get_latest_news(self, news):
        latest_news = news[0]

        for item in news:
            #   parse datetime string to datetime before comparing
            item_date_created = dateutil.parser.parse(item['date_created'])
            latest_news_date_created = dateutil.parser.parse(latest_news['date_created'])

            if item_date_created > latest_news_date_created:
                latest_news = item

        return latest_news

    def __init__(self, bot):
        #   change status
        self.bot = bot
        #self.bot.change_presence(game=discord.Game(name='MapleStory 2'))
        log.info("News Initialized!")
        
'''
    setup
'''
def setup(bot):
    bot.add_cog(News(bot))
