# Upload Assistant © 2025 Audionut & wastaken7 — Licensed under UAPL v1.0
import os
import re
from typing import Any, Optional, cast

import cli_ui
import pycountry

from src.console import console
from src.languages import languages_manager
from src.trackers.COMMON import COMMON
from src.trackers.UNIT3D import UNIT3D

Meta = dict[str, Any]
Config = dict[str, Any]


class RHD(UNIT3D):
    INVALID_TAG_PATTERN = re.compile(r"-(nogrp|nogroup|unknown|unk)", re.IGNORECASE)
    WHITESPACE_PATTERN = re.compile(r"\s{2,}")
    MARKER_PATTERN = re.compile(r"\b(UNTOUCHED|VU1080|VU720|VU)\b", re.IGNORECASE)

    def __init__(self, config: Config) -> None:
        """
        Initialize the RHD tracker client with site-specific configuration, endpoints, and defaults.
        
        Parameters:
            config (Config): Configuration object used to initialize tracker settings (URLs, credentials, and other site-specific options).
        
        Description:
            Stores the provided config, creates a COMMON helper, sets the tracker identifier to "RHD", initializes base and API endpoint URLs used by the tracker, and defines a default list of banned release groups.
        """
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
        """
        Map the media resolution in `meta` to RocketHD's internal `resolution_id`.
        
        Parameters:
            meta (Meta): Metadata mapping that must contain a `resolution` key whose value is matched against known resolution strings.
        
        Returns:
            dict[str, str]: A dictionary with key `resolution_id` containing the tracker-specific resolution identifier as a string. If the resolution is unrecognized, `'10'` is returned.
        """
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

    def get_basename(self, meta: dict[str, Any]) -> str:
        """Extract basename from first file in filelist or path"""
        path_value = next(iter(meta["filelist"]), meta["path"])
        path = path_value if isinstance(path_value, str) else ""
        return os.path.basename(path)

    def _get_language_code(self, track_or_string: Any) -> str:
        """
        Normalize a language value to an ISO 639-1 (alpha-2) code.
        
        Accepts either a mediainfo track dictionary or a language string, extracts the language,
        and normalizes it to a lowercase two-letter ISO 639-1 code when possible. Region subtags
        are removed (e.g., "en-US" → "en"). If resolution via pycountry succeeds the
        alpha-2 code is returned; otherwise the normalized input string is returned. An empty
        input yields an empty string.
        
        Parameters:
            track_or_string (Any): A mediainfo track dict (with "Language" or nested {"Language": {"String": ...}})
                or a plain language string (e.g., "English", "en", "eng", "en-US").
        
        Returns:
            str: Lowercase ISO 639-1 alpha-2 code if resolvable, otherwise the normalized input string,
            or an empty string if no language was provided.
        """
        if isinstance(track_or_string, dict):
            track_dict = cast(dict[str, Any], track_or_string)
            lang = track_dict.get("Language", "")
            if isinstance(lang, dict):
                lang = cast(dict[str, Any], lang).get("String", "")
        else:
            lang = track_or_string
        if not lang:
            return ""
        lang_str = str(lang).lower()

        # Strip country code if present (e.g., "en-US" → "en")
        if "-" in lang_str:
            lang_str = lang_str.split("-")[0]

        if len(lang_str) == 2:
            return lang_str
        try:
            lang_obj = (
                pycountry.languages.get(name=lang_str.title())
                or pycountry.languages.get(alpha_2=lang_str)
                or pycountry.languages.get(alpha_3=lang_str)
            )
            return lang_obj.alpha_2.lower() if lang_obj else lang_str
        except (AttributeError, KeyError, LookupError):
            return lang_str

    def _get_german_title(self, imdb_info: dict[str, Any]) -> Optional[str]:
        """
        Selects a German title from an IMDb AKAs list, preferring an AKA with country "Germany" and no attributes.
        
        Parameters:
            imdb_info (dict[str, Any]): IMDb information containing an "akas" entry which should be a list of dicts.
                Each AKA dict may include keys "title" (str), "country" (str), "language" (str), and "attributes".
        
        Returns:
            Optional[str]: The German title found (country-prioritized), or `None` if no suitable German AKA exists.
        """
        country_match: Optional[str] = None
        language_match: Optional[str] = None

        akas_value = imdb_info.get("akas", [])
        akas = cast(list[dict[str, Any]], akas_value) if isinstance(akas_value, list) else []
        for aka in akas:
            if aka.get("country") == "Germany" and not aka.get("attributes"):
                title = aka.get("title")
                if isinstance(title, str):
                    country_match = title
                break  # Country match takes priority
            elif aka.get("language") == "German" and not language_match and not aka.get("attributes"):
                title = aka.get("title")
                if isinstance(title, str):
                    language_match = title

        return country_match or language_match

    def _has_german_audio(self, meta: dict[str, Any]) -> bool:
        """
        Determine whether the media contains at least one German audio track that is not labeled as commentary.
        
        Parameters:
            meta (dict): Metadata dictionary expected to contain a 'mediainfo' structure with 'media' -> 'track' entries.
        
        Returns:
            bool: `true` if at least one non-commentary audio track has language code 'de', `false` otherwise.
        """
        if "mediainfo" not in meta:
            return False

        tracks = meta["mediainfo"].get("media", {}).get("track", [])
        return any(
            track.get("@type") == "Audio"
            and self._get_language_code(track) in {"de"}
            and "commentary" not in str(track.get("Title", "")).lower()
            for track in tracks[2:]
        )

    def _has_german_subtitles(self, meta: dict[str, Any]) -> bool:
        """
        Determine whether the media contains German subtitle tracks.
        
        Parameters:
        	meta (dict): Metadata dictionary expected to contain a MediaInfo-style structure under the "mediainfo" key.
        
        Returns:
        	`true` if any subtitle track (`@type` == "Text") has language code "de", `false` otherwise. If "mediainfo" is missing, returns `false`.
        """
        if "mediainfo" not in meta:
            return False

        tracks = meta["mediainfo"].get("media", {}).get("track", [])
        return any(
            track.get("@type") == "Text" and self._get_language_code(track) in {"de"}
            for track in tracks
        )

    def _get_language_name(self, iso_code: str) -> str:
        """
        Resolve an ISO language code or language name to its full language name in uppercase.
        
        Parameters:
            iso_code (str): An ISO language identifier (alpha-2 like "en", alpha-3 like "eng") or a language name (e.g., "English"). May be empty.
        
        Returns:
            str: The resolved language name in uppercase (e.g., "ENGLISH"). Returns the input uppercased if resolution fails, or an empty string for empty input.
        """
        if not iso_code:
            return ""

        iso_lower = iso_code.lower()

        # Try full language name (Italian, English, etc)
        lang = pycountry.languages.get(name=iso_code.title())
        if lang and hasattr(lang, 'name'):
            return str(lang.name).upper()

        # Try alpha_2 (IT, EN, etc)
        lang = pycountry.languages.get(alpha_2=iso_lower)
        if lang and hasattr(lang, 'name'):
            return str(lang.name).upper()

        # Try alpha_3 (ITA, ENG, etc)
        lang = pycountry.languages.get(alpha_3=iso_lower)
        if lang and hasattr(lang, 'name'):
            return str(lang.name).upper()

        return iso_code.upper()


    async def get_name(self, meta: dict[str, Any]) -> dict[str, str]:
        """
        Builds a RocketHD-style release name from the provided metadata.
        
        Constructs a normalized release title using meta fields (title, year, resolution, source, codecs, season/episode data, edition, HDR/UHD/3D flags, audio and subtitle information, repack/region markers, and other heuristics), applies optional German-title substitution, derives an audio-language tag (including multi-/dual-audio and "GERMAN SUBBED" cases), formats type-specific naming (DISC/REMUX/DVDRip/BRRip/ENCODE/HDTV/WEBDL/WEBRip), collapses extra whitespace, removes Dual-Audio markers, and appends a validated release group tag when available.
        
        Returns:
            name (dict[str, str]): Mapping with key "name" containing the generated release name string.
        """
        if not meta.get("language_checked", False):
            await languages_manager.process_desc_language(meta, tracker=self.tracker)

        # Title and basic info
        title = meta.get("title", "")
        german_title = self._get_german_title(meta.get("imdb_info", {}))
        use_german_title = self.config["TRACKERS"][self.tracker].get(
            "use_german_title", False
        )
        if german_title and use_german_title:
            title = german_title

        year_value: Any = meta.get("year", "")
        resolution_value: Any = meta.get("resolution", "")
        source_value: Any = meta.get("source", "")
        year = str(year_value)
        resolution = str(resolution_value)
        source = (
            str(cast(Any, source_value[0])) if source_value else ""
        ) if isinstance(source_value, list) else str(source_value)
        video_codec = str(meta.get("video_codec", ""))
        video_encode = str(meta.get("video_encode", ""))

        # TV specific
        season = str(meta.get("season") or "")
        episode = str(meta.get("episode") or "")
        episode_title = str(meta.get("episode_title") or "")
        part = str(meta.get("part") or "")

        # Optional fields
        edition = str(meta.get("edition") or "")
        hdr = str(meta.get("hdr") or "")
        uhd = str(meta.get("uhd") or "")
        three_d = str(meta.get("3D") or "")

        # extract tags from basename for potential later use
        basename_up = self.get_basename(meta).upper()
        anime = "ANiME" if "ANIME" in basename_up else ""
        doku = "DOKU" if "DOKU" in basename_up else ""
        internal = "iNTERNAL" if "INTERNAL" in basename_up else ""
        incomplete = "INCOMPLETE" if "INCOMPLETE" in basename_up else  ""

        # Clean audio: remove Dual-Audio and trailing language codes
        audio = meta.get("audio", "") #TODO: replace with get_best_german_audio function that handles Dual-Audio and other cases more robustly
        if "DD+" in audio:
            audio = audio.replace("DD+", "DDP")

        # Build audio language tag
        audio_lang_str = ""
        if meta.get("audio_languages"):
            # Normalize all to abbreviated ISO 639-3 codes
            audio_langs_value = meta.get("audio_languages", [])
            audio_langs_raw = cast(list[Any], audio_langs_value) if isinstance(audio_langs_value, list) else []
            audio_langs = [self._get_language_name(str(lang)) for lang in audio_langs_raw]
            audio_langs = [lang for lang in audio_langs if lang]  # Remove empty
            audio_langs = list(dict.fromkeys(audio_langs))  # Dedupe preserving order

            num_langs = len(audio_langs)

            if num_langs == 1:
                # One language (GERMAN or non-GERMAN)
                audio_lang_str = audio_langs[0]

            elif num_langs == 2:
                # Two languages ("GERMAN DL" if GERMAN is present, "[lang] DL" if not)
                if "GERMAN" in audio_langs:
                    audio_lang_str = "GERMAN DL"
                elif "ENGLISH" in audio_langs:
                    audio_lang_str = "ENGLISH DL"
                else:
                    audio_lang_str = f"{audio_langs[0]} DL"

            elif num_langs >= 3:
                # Three or more languages, "GERMAN ML" if GERMAN is present, "MULTI" only if not)
                audio_lang_str = "GERMAN ML" if "GERMAN" in audio_langs else "MULTI"

        # Add [GERMAN SUBBED] for German subtitles without German audio
        if not self._has_german_audio(meta) and self._has_german_subtitles(meta):
            audio_lang_str = "GERMAN SUBBED"

        effective_type = meta.get("type", "") #TODO: replace with get_effective_type function

        if effective_type != "DISC":
            source = source.replace("Blu-ray", "BluRay")

        # Detect Hybrid from filename if not in title
        hybrid = ""
        if (
            not edition
            and (meta.get("webdv", False) or isinstance(meta.get("source", ""), list))
            and "HYBRID" not in title.upper()
        ):
            hybrid = "Hybrid"

        repack = meta.get("repack", "").strip()

        name = None
        # Build name per RocketHD type-specific format
        if effective_type == "DISC":
            # Inject region from validated session data if available
            region = meta.get("region", "")
            if meta["is_disc"] == "BDMV":
                # BDMV: Title Year Edition REPACK Resolution 3D Hybrid Region UHD Source Audio HDR VideoCodec
                name = f"{title} {year} {season}{episode} {edition} {anime} {doku} {repack} {resolution} {three_d} {hybrid} {region} {uhd} {source} {audio} {hdr} {video_codec} {internal}"
            elif meta["is_disc"] == "DVD":
                dvd_size = meta.get("dvd_size", "")
                # DVD: Title Year Edition REPACK Resolution 3D Hybrid Region Source DVDSize Audio
                name = f"{title} {year} {season}{episode} {edition} {anime} {doku} {repack} {resolution} {three_d} {hybrid} {region} {source} {dvd_size} {audio} {internal}"
            elif meta["is_disc"] == "HDDVD":
                # HDDVD: Title Year Edition REPACK Resolution Region Source Audio VideoCodec
                name = f"{title} {year} {edition} {anime} {doku} {repack} {resolution} {region} {source} {audio} {video_codec} {internal}"

        elif effective_type == "REMUX":
            # REMUX: Title Year LANG Edition REPACK Resolution 3D Hybrid UHD Source REMUX Audio HDR VideoCodec
            name = f"{title} {year} {season}{episode} {episode_title} {part} {incomplete} {audio_lang_str} {edition} {anime} {doku} {repack} {resolution} {three_d} {hybrid} {uhd} {source} REMUX {audio} {hdr} {video_codec} {internal}"

        elif effective_type in ("DVDRIP", "BRRIP"):
            type_str = "DVDRip" if effective_type == "DVDRIP" else "BRRip"
            # DVDRip/BRRip: Title Year LANG Edition REPACK Resolution Hybrid Type Audio HDR VideoCodec
            name = f"{title} {year} {season} {incomplete} {audio_lang_str} {edition} {anime} {doku} {repack} {resolution} {hybrid} {type_str} {audio} {hdr} {video_encode} {internal}"

        elif effective_type in ("ENCODE", "HDTV"):
            # Encode/HDTV: Title Year LANG Edition REPACK Resolution Hybrid UHD Source Audio HDR VideoCodec
            name = f"{title} {year} {season}{episode} {episode_title} {part} {incomplete} {audio_lang_str} {edition} {anime} {doku} {repack} {resolution} {hybrid} {uhd} {source} {audio} {hdr} {video_encode} {internal}"

        elif effective_type in ("WEBDL", "WEBRIP"):
            service = meta.get("service", "")
            type_str = "WEB-DL" if effective_type == "WEBDL" else "WEBRip"
            # WEB: Title Year LANG Edition REPACK Resolution Hybrid UHD Type Audio service HDR VideoCodec
            name = f"{title} {year} {season}{episode} {episode_title} {part} {incomplete} {audio_lang_str} {edition} {anime} {doku} {repack} {resolution} {hybrid} {uhd} {type_str} {audio} {service} {hdr} {video_encode} {internal}"

        else:
            # Fallback: use original name
            name = str(meta["name"])


        # Ensure name is always a string
        if not name:
            name = str(meta.get("name", "UNKNOWN"))

        # Remove any leftover "Dual-Audio" markers
        if "Dual-Audio" in name:
            name = name.replace("Dual-Audio", "").strip()

        # Cleanup whitespace
        name = self.WHITESPACE_PATTERN.sub(" ", name).strip()

        # Extract tag and append if valid
        tag = self._extract_clean_release_group(meta)
        if tag:
            name = f"{name}-{tag}"

        return {"name": name}

    def _extract_clean_release_group(self, meta: dict[str, Any]) -> str:
        """
        Extract a clean release group tag from the provided metadata, accepting only VU/UNTOUCHED-like markers.
        
        Parameters:
            meta (dict): Metadata for the release; may include 'tag', 'mediainfo', and filelist/path used to derive a filename.
        
        Returns:
            str: The cleaned release group tag, or 'NOGRP' if no valid tag could be determined.
        """
        raw_tag = meta.get("tag", "")
        tag = raw_tag.strip().lstrip("-") if isinstance(raw_tag, str) else ""
        if tag and " " not in tag and not self.INVALID_TAG_PATTERN.search(tag):
            return tag

        basename = self.get_basename(meta)
        # Get extension from mediainfo and remove it
        ext = (
            meta.get("mediainfo", {})
            .get("media", {})
            .get("track", [{}])[0]
            .get("FileExtension", "")
        )
        name_no_ext = (
            basename[: -len(ext) - 1]
            if ext and basename.endswith(f".{ext}")
            else basename
        )
        parts = re.split(r"[-.]", name_no_ext)
        if not parts:
            return "NOGRP"

        potential_tag = parts[-1].strip()
        # Handle space-separated components
        if " " in potential_tag:
            potential_tag = potential_tag.split()[-1]

        if (
             potential_tag
            or len(potential_tag) > 30
            or not potential_tag.replace("_", "").isalnum()
        ):
            return "NOGRP"

        # ONLY accept if it's a VU/UNTOUCHED marker
        if not self.MARKER_PATTERN.search(potential_tag):
            return "NOGRP"

        return potential_tag

    async def get_additional_checks(self, meta: Meta) -> bool:
        """
        Run site-specific pre-upload validation checks and prompt the user to confirm or abort when a rule is violated.
        
        Performs these checks:
        - Prohibits uploads that appear to be MIC, CAM, TS, TELESYNC, LD/LINE, or marked as UPSCALE.
        - Prohibits SD resolutions (384p, 480p/480i, 540p, 576p/576i) unless explicitly overridden.
        - Requires a German audio track unless the release was requested in its original language.
        - Prohibits uploads that include sample/proof/image files in the filelist.
        
        Parameters:
            meta (Meta): Release metadata used for validation. Expected keys include `resolution`, `filelist`,
                         `requested_release`, and data used by `_has_german_audio` and `get_basename`.
        
        Returns:
            bool: `True` if the upload should proceed, `False` if the user declined to continue after a failing check.
        """
        should_continue = True

        # Uploading MIC, CAM, TS, LD, as well as upscale releases, is prohibited.
        prohib_markers = ["MIC", "CAM", "TS", "TELESYNC", "LD", "LINE", "UPSCALE"]
        basename = self.get_basename(meta)
        # Split on delimiters (dot, hyphen, underscore) or whitespace so tags like "LD" only match as separate tokens
        basename_up = [tok for tok in re.split(r'[\.\s_-]+', str(basename).upper()) if tok]
        if any(x in basename_up for x in prohib_markers):
            console.print(f"[bold red]Uploading MIC, CAM, TS, LD, as well as upscale releases, is prohibited, skipping {self.tracker} upload.")
            if not cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                return False

        # Uploading SD content is not allowed. Exception: No HD version exists. Check release databases beforehand to ensure an HD version doesn't exist
        if meta.get("resolution") in ["384p", "480p", "480i", "540p","576p", "576i"]:
            console.print(f"[bold red]Uploading SD releases is not allowed on {self.tracker}, unless no HD version exists.")
            console.print("[bold red]Please check release databases beforehand to be sure.")
            if not cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                return False

        # Uploads must contain a German audio track. Exception: The release was requested in its original language.
        if not self._has_german_audio(meta) and not meta.get("requested_release", False):
            console.print("[bold red]Uploads must contain a German audio track, unless the release was requested in its original language.")
            if not cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                return False

        # check for samples, proofs, and images in the upload directory
        filelist = meta.get("filelist", [])
        if any(
            str(file).lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".pdf"))
            or "sample" in str(file).lower()
            or "proof" in str(file).lower()
            for file in filelist
        ):
            console.print("[bold red]Uploads containing samples, proofs, and images are prohibited.[/bold red]")
            if not cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                return False
        return should_continue