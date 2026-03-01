from typing import Any
import asyncio
import requests
from difflib import SequenceMatcher
import os
import platform
import bencodepy
import httpx
import re
import cli_ui
from src.trackers.COMMON import COMMON
from src.console import console


class FLD:
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """
    def __init__(self, config):
        self.config = config
        self.tracker = 'FLD'
        self.source_flag = 'FLD'
        self.upload_url = 'https://flood.st/api/torrents/upload'
        self.signature = "\n[align=center][size=1][url=https://github.com/Audionut/Upload-Assistant]Created by Audionut's Upload Assistant[/url][/size][/align]"
        self.banned_groups = ['4K4U', 'AOC', 'C4K', 'CRUCiBLE', 'd3g', 'EASports', 'FGT', 'MeGusta', 'MezRips', 'nikt0', 'ProRes', 'RARBG', 'ReaLHD', 'SasukeducK', 'Sicario', 'TEKNO3D', 'Telly', 'tigole', 'TOMMY', 'WKS', 'x0r', 'YIFY']

    async def upload(self, meta: dict[str, Any], _disctype: str) -> bool:
        common = COMMON(config=self.config)
        announce_url = self.config['TRACKERS'][self.tracker]['announce_url']
        await common.create_torrent_for_upload(meta, self.tracker, self.source_flag, announce_url=announce_url)
        media_type = await self.get_media_type(meta)
        await self.edit_desc(meta)
        fld_name = await self.edit_name(meta)
        tmdb_id = await self.get_prefixed_tmdb_id(meta)

        if not self.config['TRACKERS'][self.tracker].get('anon', False):
            anon = ''
        else:
            anon = 'checked'

        if meta['bdinfo'] is not None:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8')
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8')

        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r', encoding='utf-8').read()
        torrent_file = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}].torrent"
        files = dict()
        open_torrent = None
        if os.path.exists(torrent_file):
            open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}].torrent", 'rb')
            files['meta_info'] = open_torrent.read()

        data = {
            'name': fld_name,
            'imdb_id': meta['imdb'],
            'tmdb_id': tmdb_id,
            'anonymous': anon,
            'description': desc,
            'media_info': mi_dump.read(),
            'media_type': media_type,
        }

        headers = {
            'User-Agent': f'Upload Assistant/2.2 ({platform.system()} {platform.release()})',
            'Authorization': f"Bearer {self.config['TRACKERS'][self.tracker]['api_key'].strip()}"
        }

        if meta['debug'] is False:
            request = requests.post(url=self.upload_url, files=files, data=data, headers=headers)
            response = request.json()
            meta['tracker_status'][self.tracker]['status_message'] = response

            if not response["success"]:
                console.print(f"[red]Upload failed: {response['message']}")
                return False
        else:
            console.print("[cyan]Request Data:")
            console.print(data)

        try:
            open_torrent.seek(0)
            torrent_data = open_torrent.read()
            torrent = bencodepy.decode(torrent_data)
            torrent[b'comment'] = response['torrent_url'].encode('utf-8')
            with open(torrent_file, 'wb') as updated_torrent_file:
                updated_torrent_file.write(bencodepy.encode(torrent))

            if meta['debug']:
                console.print(f"Torrent file updated with comment: {response['torrent_url']}")
        except Exception as e:
            console.print(f"Error while editing the torrent file: {e}")

        if open_torrent is not None:
            open_torrent.close()
            return True
        return False

    async def get_media_type(self, meta):
        is_tv_pack = meta.get('tv_pack', 0) == 1
        return {
            'MOVIE': 'movie',
            'TV': 'show_season' if is_tv_pack else 'show_episode',
        }.get(meta['category'], 'MOVIE')

    async def get_prefixed_tmdb_id(self, meta):
        if meta['category'] == 'TV':
            return f"tv/{meta['tmdb']}"
        else:
            return f"movie/{meta['tmdb']}"

    async def edit_desc(self, meta):
        base = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/DESCRIPTION.txt", 'r', encoding='utf-8').read()
        base = base.replace("[user]", "").replace("[/user]", "")
        with open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'w', encoding='utf-8') as desc:
            if meta.get('discs', []) != []:
                discs = meta['discs']
                if discs[0]['type'] == "DVD":
                    desc.write(f"[spoiler=VOB MediaInfo][code]{discs[0]['vob_mi']}[/code][/spoiler]")
                    desc.write("\n")
                if len(discs) >= 2:
                    for each in discs[1:]:
                        if each['type'] == "BDMV":
                            desc.write(f"[spoiler={each.get('name', 'BDINFO')}][code]{each['summary']}[/code][/spoiler]")
                            desc.write("\n")
                        elif each['type'] == "DVD":
                            desc.write(f"{each['name']}:\n")
                            desc.write(f"[spoiler={os.path.basename(each['vob'])}][code][{each['vob_mi']}[/code][/spoiler] [spoiler={os.path.basename(each['ifo'])}][code][{each['ifo_mi']}[/code][/spoiler]")
                            desc.write("\n")
                        elif each['type'] == "HDDVD":
                            desc.write(f"{each['name']}:\n")
                            desc.write(f"[spoiler={os.path.basename(each['largest_evo'])}][code][{each['evo_mi']}[/code][/spoiler]\n")
                            desc.write("\n")
            desc.write(base.replace("[img]", "[img width=300]"))
            if meta.get('comparison') and meta.get('comparison_groups'):
                desc.write("[center]")
                comparison_groups = meta.get('comparison_groups', {})
                sorted_group_indices = sorted(comparison_groups.keys(), key=lambda x: int(x))

                comp_sources = []
                for group_idx in sorted_group_indices:
                    group_data = comparison_groups[group_idx]
                    group_name = group_data.get('name', f'Group {group_idx}')
                    comp_sources.append(group_name)

                sources_string = ", ".join(comp_sources)
                desc.write(f"[comparison={sources_string}]\n")

                images_per_group = min([
                    len(comparison_groups[idx].get('urls', []))
                    for idx in sorted_group_indices
                ])

                for img_idx in range(images_per_group):
                    for group_idx in sorted_group_indices:
                        group_data = comparison_groups[group_idx]
                        urls = group_data.get('urls', [])
                        if img_idx < len(urls):
                            img_url = urls[img_idx].get('raw_url', '')
                            if img_url:
                                desc.write(f"{img_url}\n")

                desc.write("[/comparison][/center]\n\n")
            if f'{self.tracker}_images_key' in meta:
                images = meta[f'{self.tracker}_images_key']
            else:
                images = meta['image_list']
            if len(images) > 0:
                desc.write("[align=center]")
                for each in range(len(images[:int(meta['screens'])])):
                    web_url = images[each]['web_url']
                    img_url = images[each]['img_url']
                    if (each == len(images) - 1):
                        desc.write(f"[url={web_url}][img width=350]{img_url}[/img][/url]")
                    elif (each + 1) % 2 == 0:
                        desc.write(f"[url={web_url}][img width=350]{img_url}[/img][/url]\n")
                        desc.write("\n")
                    else:
                        desc.write(f"[url={web_url}][img width=350]{img_url}[/img][/url] ")
                desc.write("[/align]")
            desc.write(self.signature)
            desc.close()
        return

    async def search_existing(self, _meta: dict[str, Any], _disctype: str) -> list[str]:
        console.print("dupe check for FLD is disabled, please check yourself")
        return []


    async def edit_name(self, meta):
        name = meta.get('name')
        if meta.get('source', '') in ('PAL DVD', 'NTSC DVD', 'DVD', 'NTSC', 'PAL'):
            audio = meta.get('audio', '')
            audio = ' '.join(audio.split())
            name = name.replace(audio, f"{meta.get('video_codec')} {audio}")
        name = name.replace("DD+", "DDP")
        return name

