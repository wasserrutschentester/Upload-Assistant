# Upload Assistant © 2025 Audionut & wastaken7 — Licensed under UAPL v1.0
# import discord
from typing import Any, Optional

from src.trackers.COMMON import COMMON
from src.trackers.UNIT3D import UNIT3D
import json

Meta = dict[str, Any]
Config = dict[str, Any]


class RHD(UNIT3D):
    def __init__(self, config: Config) -> None:
        super().__init__(config, tracker_name='RHD')
        self.config = config
        self.common = COMMON(config)
        self.tracker = 'RHD'
        self.base_url = 'https://rocket-hd.cc'
        self.id_url = f'{self.base_url}/api/torrents/'
        self.upload_url = f'{self.base_url}/api/torrents/upload'
        self.requests_url = f'{self.base_url}/api/requests/filter'  # If the site supports requests via API, otherwise remove this line
        self.search_url = f'{self.base_url}/api/torrents/filter'
        self.torrent_url = f'{self.base_url}/torrents/'
        self.banned_groups = ["1XBET", "MEGA", "MTZ", "Whistler", "WOTT", "Taylor.D", "HELD", "FSX", "FuN", "MagicX", "w00t", "PaTroL", "BB",
                              "266ers", "GTF", "JellyfinPlex", "2BA", "FritzBox"]
        pass

    # The section below can be deleted if no changes are needed, as everything else is handled in UNIT3D.py
    # If advanced changes are required, copy the necessary functions from UNIT3D.py here
    # For example, if you need to modify the description, copy and paste the 'get_description' function and adjust it accordingly

    async def get_resolution_id(
        self,
        meta: Meta,
        resolution: Optional[str] = None,
        reverse: bool = False,
        mapping_only: bool = False,
    ) -> dict[str, str]:
        _ = (resolution, reverse, mapping_only)
        resolution_id = {
            '8640p': '10',
            '4320p': '1',
            '2160p': '2',
            '1440p': '3',
            '1080p': '3',
            '1080i': '4',
            '720p': '5',
            '576p': '12',
            '576i': '13',
            '540p': '16',
            '480p': '11',
            '480i': '18',
            '384p': '14',
        }.get(meta['resolution'], '10')
        return {'resolution_id': resolution_id}

    def get_language_tag(self, meta):
        audio_languages = []
        text_languages = []
        lang_tag = ""
        audio_codec = ""
        ignored_keywords = ["commentary", "music", "director", "cast", "party"]
        german_language_codes = ["de", "deu", "ger"]
        english_language_codes = ["en", "eng"]

        if meta['is_disc'] != "BDMV":
            with open(f"{meta.get('base_dir')}/tmp/{meta.get('uuid')}/MediaInfo.json", 'r',
                      encoding='utf-8') as f:
                mi = json.load(f)

            german_audio_tracks = []
            for track in mi['media']['track']:
                if track.get('@type') == 'Audio':
                    title = track.get('Title', '')
                    title = title.lower() if isinstance(title, str) else ''
                    if not any(keyword in title for keyword in ignored_keywords):
                        language = track.get('Language', '').lower()
                        if language:
                            audio_languages.append(language)
                            if language in german_language_codes:
                                extra_str = ''
                                channels = track.get('Channels', '0')
                                format_str = track.get('Format', '')
                                additional_features = track.get('Format_AdditionalFeatures', '')
                                new_format_str = format_str

                                if 'JOC' in additional_features:
                                    extra_str = ' ATMOS'

                                if '16-ch' in additional_features:
                                    new_format_str = format_str.replace(' 16-ch', '')
                                    extra_str = ' ATMOS'

                                replacements = {
                                    "E-AC-3": "DDP",
                                    "AC-3": "DD",
                                    "DTS ES XLL": "DTS-HD MA ES",
                                    "DTS XBR": "DTS:X",
                                    "DTS XLL": "DTS-HD MA",
                                    "MLP FBA": "TrueHD",
                                    "PCM": "LPCM",
                                }

                                for src, target in replacements.items():
                                    new_format_str = new_format_str.replace(src, target)

                                channel_notation = {'6': '5.1', '8': '7.1'}.get(channels,
                                                                                f"{channels}.0")
                                codec = f"{new_format_str} {channel_notation}{extra_str}"

                                german_audio_tracks.append(
                                    {'codec': codec, 'channels': int(channels)})
                elif track.get('@type') == 'Text':
                    language = track.get('Language', '').lower()
                    if language:
                        text_languages.append(language)

            # Select German track with most channels
            if german_audio_tracks:
                audio_codec = max(german_audio_tracks, key=lambda x: x['channels'])['codec']

        else:
            with open(f"{meta.get('base_dir')}/tmp/{meta.get('uuid')}/BD_SUMMARY_00", 'r',
                      encoding='utf-8') as f:
                bd_summary = f.read()

            # Extract audio and subtitle languages
            audio_languages = re.findall(r"Audio:\s*([^/]+)", bd_summary, re.IGNORECASE)
            subtitle_languages = re.findall(r"Subtitle:\s*([^/]+)", bd_summary, re.IGNORECASE)
            audio_languages = [lang.strip().lower() for lang in
                               audio_languages] if audio_languages else []
            text_languages = [lang.strip().lower() for lang in
                              subtitle_languages] if subtitle_languages else []

            # Extract German audio codec
            german_audio_tracks = []
            for line in bd_summary.split('\n'):
                if 'Audio:' in line and 'German' in line:
                    match = re.search(r"Audio:.*?/ ([^/]+) / (\d\.\d)", line, re.IGNORECASE)
                    if match:
                        format_str, channel_notation = match.groups()
                        format_str = format_str.strip()
                        if format_str == 'DTS-HD Master Audio':
                            format_str = 'DTS HD-MA'
                        elif format_str == 'Dolby Digital Plus':
                            format_str = 'DDP'
                        elif format_str == 'Dolby Digital':
                            format_str = 'DD'
                        channels = 6 if channel_notation == '5.1' else 8 if channel_notation == '7.1' else 2 if channel_notation == '2.0' else '1.0'
                        codec = f"{format_str} {channel_notation}"
                        german_audio_tracks.append({'codec': codec, 'channels': channels})

            # Select German track with most channels
            if german_audio_tracks:
                audio_codec = max(german_audio_tracks, key=lambda x: x['channels'])['codec']

        has_german_audio = any(code in german_language_codes for code in audio_languages)
        has_english_audio = any(code in english_language_codes for code in audio_languages)
        has_german_subtitles = any(code in german_language_codes for code in text_languages)
        distinct_audio_languages = set(audio_languages)  # Remove duplicates

        if not has_german_audio:
            console.print("[yellow]WARN: No german track found. This is only allowed for requested media.")

        if has_german_audio and len(distinct_audio_languages) == 1:
            lang_tag = "GERMAN"
        elif has_german_audio and len(distinct_audio_languages) == 2:
            lang_tag = "GERMAN DL"
        elif has_german_audio and len(distinct_audio_languages) > 2:
            lang_tag = "GERMAN ML"
        elif not has_german_audio and has_german_subtitles:
            lang_tag = "GERMAN SUBBED"
        elif not has_german_audio and not has_german_subtitles and has_english_audio:
            lang_tag = "ENGLISH"

        return lang_tag, audio_codec

    async def get_name(self, meta: Meta) -> dict[str, str]:
        rhd_name = meta.get('name', '')

        lang_tag, audio_codec = self.get_language_tag(meta)

        # Replace audio with German audio_codec
        if meta.get('audio') and audio_codec:
            rhd_name = rhd_name.replace(meta['audio'], audio_codec)

        _known = {
            part.upper()
            for part in [meta.get('cut'),
                         meta.get('edition'),
                         meta.get('ratio'),
                         meta.get('repack'),
                         meta.get('resolution') if meta.get('resolution') != "OTHER" else "",
                         meta.get('source'),
                         meta.get('uhd')
                         ]
            if part
        }

        if lang_tag:
            name_parts = rhd_name.split()
            existing_lang_tags = {"GERMAN", "GERMAN DL", "GERMAN ML", "GERMAN SUBBED"}
            name_parts = [part for part in name_parts if part.upper() not in existing_lang_tags]

            insert_index = next(
                (i for i, part in enumerate(name_parts) if part.upper() in _known),
                len(name_parts)
            )
            name_parts.insert(insert_index, lang_tag)
            rhd_name = ' '.join(name_parts)

        if lang_tag == "GERMAN DL":
            rhd_name = rhd_name.replace("Dual-Audio ", "")

        if not meta.get('tag') and not (
                rhd_name.endswith("-NOGRP") or rhd_name.endswith("-NOGROUP")):
            rhd_name += " -NOGRP"

        return {'name': ' '.join(rhd_name.split()) }
