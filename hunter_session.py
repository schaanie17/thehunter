import json
import re
import requests
import urllib
import datetime
import os.path
#from   tqdm.notebook import tqdm
from   stqdm         import stqdm as tqdm
import more_itertools

import pymongo


class Session(requests.Session):
    def __init__(self,mongo_url):
        super().__init__()
        self.token_data = None
        self.oauth_data = None
        self.mongo_url  = mongo_url

        self.mongo_client = pymongo.MongoClient(self.mongo_url)
        self.cache = self.mongo_client.thehunter_cache
        
    def connect(self,username,password):
        self.token_data = None
        
        data = urllib.parse.urlencode({"email": username, "password": password})
        resp = self.post("https://www.thehunter.com/login?xhr=true&return_to=/",data=data)
        resp = self.get ("https://www.thehunter.com/#feed"                               )

        m = re.search(r'var userAccessToken = "(\w+)";',resp.text)
        if m:
            token = m[1]
        else:
            raise RuntimeError("Incorrect name or password")

        self.token_data = urllib.parse.urlencode({"oauth_access_token": token})

        oauth = re.search(r'oauth_consumer_key: "(\w+)"',   resp.text)[1]
        self.oauth_data = urllib.parse.urlencode({"oauth_consumer_key": oauth})

    def load_app(self):
        resp = self.post("https://api.thehunter.com/v1/Application/application",data=self.oauth_data)
        self.app = json.loads(resp._content)

        self.missions = dict([(m["id"],m) for m in self.app["missions"]])
        self.species  = dict([(s["id"],s) for s in self.app["species" ]])
        self.reserves = dict([(r["id"],r) for r in self.app["reserves"]])
        self.items    = dict([(i["id"],i) for i in self.app["items"   ]])

        # add mission group to the individual missions
        self.missionGroups = {}
        for mg in self.app["mission_groups"]:
            mgid = mg["id"]
            self.missionGroups[mgid] = mg
            for mid in mg["missions"]:
                self.missions[mid]["missionGroup"] = mgid

        # add special mission group for stand-alone missions
        self.missionGroups[-1] = {
            "title"    : "Special Missions",
            "missions" : [],    
        }
        for mid,m in self.missions.items():
            if "missionGroup" not in m:
                m["missionGroup"] = -1
                self.missionGroups[-1]["missions"].append(mid)

    def load_me(self):
        resp = self.post("https://api.thehunter.com/v1/Me/me", data=self.token_data)
        self.me = json.loads(resp._content)
        self.myItems = dict((int(iid),cnt) for iid,cnt in self.me["items"].items())
        
    def load_missions(self):
        resp = self.post("https://api.thehunter.com/v1/Mission/missions", data=self.token_data)
        self.myMissions = json.loads(resp._content)        
        
        self.activeMissions = self.myMissions["active"]
        self.missionStates  = dict((int(mid),s) for mid,s in self.myMissions["states"].items())

        # add completed objectives to each mission
        for mid,s in self.missionStates.items():
            if s["state"] == 2:
                self.missions[mid]['completedObjectives'] = s["objectives"]

    def __load_expedition_list(self,user_id,limit=50):
        offset = 0
        while True:
            data = {
                "user_id" : self.me["id"],
                "offset"  : offset,
                "limit"   : limit,
            }
            resp = self.post("https://api.thehunter.com/v1/Expedition/list", data=data)
            d = json.loads(resp._content)

            expOffset = offset+limit

            for e in d["expeditions"]:
                yield e
                offset += 1
            
            if offset < expOffset:
                break        

    def load_expeditions(self,user_id):
        import streamlit as st

        limit  = 40
        offset = 0

        eDict = dict((e["id"],e) for e in self.__load_expedition_list(user_id))
        self.myExpeditions = {}

        for eids in more_itertools.ichunked(list(eDict.keys()),30):
            for e in self.cache.expeditions.find({"_id" : {"$in" : list(eids)}}):
                self.myExpeditions[e["id"]] = e
                del eDict[e["id"]]

        total = len(eDict)
        for e in tqdm(eDict.values(),total=total):
            data = {
                "user_id"       : user_id,
                "expedition_id" : e["id"],
            }
            resp = self.post("https://api.thehunter.com/v1/Public_user/expedition", data=data)
            e2 = json.loads(resp._content)
            e.update(e2["expedition"])
            del e2["expedition"]
            e.update(e2)
            e["_id"] = e["id"]

            self.myExpeditions[e["id"]] = e

        if eDict:
            self.cache.expeditions.insert_many(list(eDict.values()))

        self.kills = []
        for e in self.myExpeditions.values():
            self.kills.extend(e["kills"])

        self.speciesKills = {}
        for k in self.kills:
            self.speciesKills.setdefault(k["species"],[]).append(k)


    def _reserveKeyword(self,r):
        """ Extract keywords from a reserve. 
        Whitehart Island is sometimes referred to just as Whitehart and the apostrophe 
        in Logger's Point is used inconsistently. """

        nm = r["name"]
        if   nm == "Whitehart Island": return ("Whitehart",     nm)
        elif nm == "Logger's Point":   return ("Loggers Point", nm)
        else:                          return (nm,)

    def _speciesKeyword(self,s):
        """ Extract keywords from a species. 
        Use only Typical variants and delete Non-Typical (e.g. for Mule and *tail deer). """

        nm = s["name"]
        if   nm.endswith(" (Typical)"):     return (nm[:-10],)
        elif nm.endswith(" (Non-Typical)"): return tuple()
        else:                               return (nm,)

    def _itemKeyword(self,i):
        """ Extract keywords for an item """

        nm  = i["name"]
        snm = i["shortname"]
        if   nm == "Compound Bow \"Parker Python\"": return ("Parker Python Compound Bow",nm,snm)
        elif nm.startswith("Aimpoint"):              return (nm,"Aimpoint Sight")
        elif snm is not None:                        return (nm,snm)
        else:                                        return (nm,)        

    def collectBadKeywords(self,rid):
        """ Collect all bad keywords """

        badKeywords  = set()
        goodKeywords = set()

        # get selected reserve from id
        reserve = self.reserves[rid]["name"]

        goodKeywords.add(reserve)

        # add keywords for all other reserves
        for orid,r in self.reserves.items():
            if rid != orid:
                badKeywords.update(self._reserveKeyword(r))

        # add keywords for the species in the selected reserve
        for sid in self.reserves[rid]["species"]:
            goodKeywords.update(self._speciesKeyword(self.species[sid]))

        # add keywords for all species that are not in the selected reserve
        for sid,s in self.species.items():
            if sid not in self.reserves[rid]["species"]:
                badKeywords.update(self._speciesKeyword(s))

        # add keywords for all my items
        for iid,count in self.myItems.items():
            if count[0] > 0:
                goodKeywords.update(self._itemKeyword(self.items[iid]))

        # add keywords for all items that I do not own
        for iid,i in self.items.items():
            if iid not in self.myItems.keys() or self.myItems[iid][0] == 0:
                badKeywords.update(self._itemKeyword(i))

        # Remove good keywords from bad keywords
        # e.g. if the selected reserve has a Willow Ptarmigan resulting in a good keyword "Ptarmigan"
        # and the bad keywords contain "Ptarmigan" because of the "Rock Ptarmigan", then a mission which
        # mentions just a Ptarmigan shall not be filtered out
        badKeywords -= goodKeywords

        self.badKeywords = badKeywords

    def _checkKeywords(self,titles):
        """ Check whether at least one of the keywords appears in one of the titles. """

        vlds = []
        newTitles = []
        for ti in titles:
            pattern = f"({'|'.join(re.escape(kw) for kw in self.badKeywords)})"
            newTi,n = re.subn(pattern,r"<mark>\1</mark>",ti,flags=re.IGNORECASE)
            newTitles.append(newTi)
            vlds.append(n == 0)
        return vlds,newTitles

    def filterMissions(self):
        """ Filter missions that contain no bad keywords """

        goodMissions = []
        badMissions  = []

        for mid in self.activeMissions:
            m  = self.missions[mid]
            mg = self.missionGroups[m["missionGroup"]]

            mgTitle = mg["title"]
            mTitle  = m["title"]
            tTitles = tuple(obj["title"] for obj in m["objectives"])

            goodMission = True

            (mgVld,mVld,*tVlds),(mgtitle,mTitle,*tTitles) = self._checkKeywords((mgTitle,mTitle)+tTitles)
            result = (m,mgtitle,mTitle,tTitles)

            if not mgVld or not mVld:
                goodMission = False

            if m["singleExpedition"]:
                for vld in tVlds:
                    if vld is False:
                        goodMission = False
            else:
                tmp = False
                for vld in tVlds:
                    if vld is True:
                        tmp = True
                if tmp is False:
                    goodMission = False

            if goodMission:
                goodMissions.append(result)
            else:
                badMissions.append(result)
                
        return goodMissions,badMissions
