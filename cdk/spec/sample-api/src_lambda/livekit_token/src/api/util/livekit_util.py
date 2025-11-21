import os
import asyncio
import logging
from typing import Union

from livekit import api, rtc
from livekit.api import LiveKitAPI
from .config import LIVEKIT_ENV

logging.basicConfig(
    level=logging.INFO,
)


async def cancel_all_tasks(loop=None):
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


class LiveKitManager:
    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        url: str | None = None,
        *,
        livekit_server_type: str,
    ):
        if livekit_server_type not in LIVEKIT_ENV:
            raise Exception(f"livekit config not defined for `{livekit_server_type}`")

        config = LIVEKIT_ENV[livekit_server_type]
        api_key = self._resolve_env("LIVEKIT_API_KEY", config, api_key)
        api_secret = self._resolve_env("LIVEKIT_API_SECRET", config, api_secret)
        url = self._resolve_env("LIVEKIT_URL", config, url)

        if api_key is None or api_secret is None or url is None:
            raise Exception(
                "please set LIVEKIT_API_KEY, LIVEKIT_API_SECRET and LIVEKIT_URL as env var or in config file"
            )
        print(f"LiveKitManager target url: {url}")
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = url

    @staticmethod
    def _resolve_env(
        key: str, config: dict[str, str], override_value: str | None = None
    ):
        if override_value is not None:
            return override_value
        return os.getenv(key, config[key])

    async def get_api_async(self):
        return LiveKitAPI(self.url, self.api_key, self.api_secret)

    async def connect_room(self, identity: str, name: str, room_name: str):
        os.makedirs("log", exist_ok=True)
        self.room_log = logging.getLogger("room")
        self.room_log.addHandler(logging.FileHandler(f"log/{room_name}.log"))

        room = rtc.Room()
        token = self.create_token(
            identity,
            name,
            room_name,
        )
        self.add_logging_listener(room)
        await room.connect(self.url, token)
        self.room_log.info("connected to room %s", room.name)
        self.room_log.info("participants: %s", room.remote_participants)

        return room

    def add_logging_listener(self, room):
        @room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant) -> None:
            self.room_log.info(
                "participant connected: %s %s", participant.sid, participant.identity
            )

        @room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            self.room_log.info(
                "participant disconnected: %s %s", participant.sid, participant.identity
            )

        @room.on("local_track_published")
        def on_local_track_published(
            publication: rtc.LocalTrackPublication,
            track: Union[rtc.LocalAudioTrack, rtc.LocalVideoTrack],
        ):
            self.room_log.info("local track published: %s", publication.sid)

        @room.on("active_speakers_changed")
        def on_active_speakers_changed(speakers: list[rtc.Participant]):
            self.room_log.info("active speakers changed: %s", speakers)

        @room.on("local_track_unpublished")
        def on_local_track_unpublished(publication: rtc.LocalTrackPublication):
            self.room_log.info("local track unpublished: %s", publication.sid)

        @room.on("track_published")
        def on_track_published(
            publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
        ):
            self.room_log.info(
                "track published: %s from participant %s (%s)",
                publication.sid,
                participant.sid,
                participant.identity,
            )

        @room.on("track_unpublished")
        def on_track_unpublished(
            publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
        ):
            self.room_log.info("track unpublished: %s", publication.sid)

        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            self.room_log.info("track subscribed: %s", publication.sid)
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                _video_stream = rtc.VideoStream(track)
                # video_stream is an async iterator that yields VideoFrame
            elif track.kind == rtc.TrackKind.KIND_AUDIO:
                print("Subscribed to an Audio Track")
                _audio_stream = rtc.AudioStream(track)
                # audio_stream is an async iterator that yields AudioFrame

        @room.on("track_unsubscribed")
        def on_track_unsubscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            self.room_log.info("track unsubscribed: %s", publication.sid)

        @room.on("track_muted")
        def on_track_muted(
            publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
        ):
            self.room_log.info("track muted: %s", publication.sid)

        @room.on("track_unmuted")
        def on_track_unmuted(
            publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant
        ):
            self.room_log.info("track unmuted: %s", publication.sid)

        @room.on("data_received")
        def on_data_received(data: rtc.DataPacket):
            if data.participant is not None:
                self.room_log.info(
                    "received data from %s: %s", data.participant.identity, data.data
                )

        @room.on("connection_quality_changed")
        def on_connection_quality_changed(
            participant: rtc.Participant, quality: rtc.ConnectionQuality
        ):
            self.room_log.info(
                "connection quality changed for %s", participant.identity
            )

        @room.on("track_subscription_failed")
        def on_track_subscription_failed(
            participant: rtc.RemoteParticipant, track_sid: str, error: str
        ):
            self.room_log.info(
                "track subscription failed: %s %s", participant.identity, error
            )

        @room.on("connection_state_changed")
        def on_connection_state_changed(state: rtc.ConnectionState):
            self.room_log.info("connection state changed: %s", state)

        @room.on("connected")
        def on_connected() -> None:
            self.room_log.info("connected")

        @room.on("disconnected")
        def on_disconnected() -> None:
            self.room_log.info("disconnected")

        @room.on("reconnecting")
        def on_reconnecting() -> None:
            self.room_log.info("reconnecting")

        @room.on("reconnected")
        def on_reconnected() -> None:
            self.room_log.info("reconnected")

    def create_token(
        self,
        identity: str,
        name: str,
        room_name: str,
    ) -> str:

        token = (
            api.AccessToken(self.api_key, self.api_secret)
            .with_identity(identity)
            .with_name(name)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                )
            )
        )
        return token.to_jwt()
