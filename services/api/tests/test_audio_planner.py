from app.config import get_settings
from app.schemas import AlignmentResult, AudioSegment, CaptionCue, NarrationSegment, TimelineClip, TimelinePlan
from app.services.audio_planner import apply_audio_editorial
from app.services.narration import _audio_intent


def _clip(start: float, end: float, source: str, narration_id: str, source_start: float = 0.0) -> TimelineClip:
    span = end - start
    return TimelineClip(
        start=start,
        end=end,
        source=source,
        source_start=source_start,
        source_end=round(source_start + span, 3),
        narration_segment_id=narration_id,
        crop_mode="blur-background",
    )


def _audio(**kwargs) -> AudioSegment:
    return AudioSegment.model_validate(kwargs)


def test_audio_planner_uses_vo_bite_nat_and_mutes_irrelevant_speech() -> None:
    narration = [
        NarrationSegment(
            id="narration_01",
            start=0.0,
            end=6.0,
            text="টানা বৃষ্টিতে বাড়ছে নদীর জলস্তর।",
            type="event",
        ),
        NarrationSegment(
            id="narration_02",
            start=6.0,
            end=14.0,
            text="তিন দিন ধরে এখানে জল জমে আছে এবং বাসিন্দারা কষ্টে আছেন।",
            type="event",
        ),
        NarrationSegment(
            id="narration_03",
            start=14.0,
            end=20.0,
            text="সেচ দপ্তর পরিস্থিতি পর্যবেক্ষণ করছে।",
            type="close",
        ),
    ]
    plan = TimelinePlan(
        headline="দুর্গাপুরে জল",
        location="দুর্গাপুর",
        duration=20.0,
        timeline=[
            _clip(0, 6, "video01.mp4", "narration_01"),
            _clip(6, 14, "video03.mp4", "narration_02"),
            _clip(14, 20, "video06.mp4", "narration_03"),
        ],
        captions=[CaptionCue(start=0, end=20, text="টানা বৃষ্টিতে বাড়ছে নদীর জলস্তর")],
    )
    segments = [
        _audio(
            id="audio_video01_01",
            source_file="video01.mp4",
            start=0.0,
            end=8.0,
            contains_speech=False,
            transcript="",
            speaker_type="environment",
            audio_type="natural_sound",
            speech_quality=0.0,
            information_value=0.2,
            news_relevance=0.4,
            rms=0.06,
            peak=0.4,
            playback_gain=1.0,
        ),
        _audio(
            id="audio_video02_01",
            source_file="video02.mp4",
            start=2.0,
            end=6.0,
            contains_speech=True,
            transcript="চা খান তাহলে চলুন বাজারে যাই",
            speaker_type="unknown",
            audio_type="irrelevant_speech",
            speech_quality=0.8,
            information_value=0.05,
            news_relevance=0.04,
            rms=0.07,
            peak=0.5,
            playback_gain=1.0,
        ),
        _audio(
            id="audio_video03_01",
            source_file="video03.mp4",
            start=0.0,
            end=4.0,
            contains_speech=False,
            transcript="",
            speaker_type="environment",
            audio_type="ambient_sound",
            rms=0.01,
        ),
        _audio(
            id="audio_video04_01",
            source_file="video04.mp4",
            start=12.2,
            end=21.8,
            contains_speech=True,
            transcript="তিন দিন ধরে এখানে জল জমে আছে",
            speaker_type="local_resident",
            audio_type="local_resident_bite",
            speech_quality=0.83,
            information_value=0.91,
            news_relevance=0.94,
            rms=0.08,
            peak=0.5,
            playback_gain=1.0,
        ),
        _audio(
            id="audio_video05_01",
            source_file="video05.mp4",
            start=3.0,
            end=9.0,
            contains_speech=True,
            transcript="আমি দুর্গাপুর ব্যারেজে দাঁড়িয়ে এই মুহূর্তে",
            speaker_type="reporter",
            audio_type="reporter_standup",
            speech_quality=0.88,
            information_value=0.4,
            news_relevance=0.2,
            rms=0.07,
            peak=0.45,
            playback_gain=1.0,
        ),
        _audio(
            id="audio_video06_01",
            source_file="video06.mp4",
            start=1.0,
            end=5.0,
            contains_speech=True,
            transcript="এই শব্দটা কাজের না",
            speaker_type="unknown",
            audio_type="unusable_audio",
            speech_quality=0.15,
            news_relevance=0.02,
            rms=0.01,
        ),
    ]
    alignment = AlignmentResult(
        duration=20.0,
        cues=[
            CaptionCue(start=0, end=6, text="টানা বৃষ্টিতে বাড়ছে নদীর জলস্তর।"),
            CaptionCue(start=6, end=14, text="তিন দিন ধরে এখানে জল জমে আছে।"),
            CaptionCue(start=14, end=20, text="সেচ দপ্তর পরিস্থিতি পর্যবেক্ষণ করছে।"),
        ],
    )

    result, debug = apply_audio_editorial(plan, narration, segments, alignment, get_settings())
    modes = [clip.audio.mode for clip in result.timeline]
    assert "SOURCE_SOUNDBITE" in modes
    assert "VOICEOVER_ONLY" in modes
    assert "VOICEOVER_WITH_NAT_SOUND" not in modes

    bite = next(clip for clip in result.timeline if clip.audio.mode == "SOURCE_SOUNDBITE")
    assert bite.source == "video04.mp4"
    assert bite.source_start == 12.2
    assert bite.audio.voice_volume == 0
    assert bite.audio.source_volume > 0
    assert bite.audio.editorial_action == "REPLACE_VOICEOVER"
    assert bite.audio.voiceover_enabled is False

    voice_only = [clip for clip in result.timeline if clip.audio.mode == "VOICEOVER_ONLY"]
    assert voice_only
    assert all(clip.audio.source_volume == 0 and clip.audio.voice_volume == 1 for clip in voice_only)

    used_audio = {clip.audio.audio_segment_id for clip in result.timeline}
    assert "audio_video02_01" not in used_audio
    assert "audio_video06_01" not in used_audio

    muted = [candidate for row in debug for candidate in row.candidates if candidate.audio_id == "audio_video02_01"]
    assert muted
    assert all(item.decision == "MUTE" for item in muted)

    bite_caption = next(cue for cue in result.captions if cue.source == "VIDEO_SOUNDBITE")
    assert "জল জমে" in bite_caption.text
    assert all(not (clip.audio.voice_volume > 0 and clip.audio.source_volume > 0) for clip in result.timeline)
    assert abs(result.timeline[0].start) < 0.01
    assert abs(result.timeline[-1].end - result.duration) < 0.05


def test_script_intent_inserts_field_voice_without_transcript() -> None:
    narration = [
        NarrationSegment(
            id="narration_01",
            start=0.0,
            end=5.0,
            text="জলমগ্ন বীরভানপুরে স্থানীয়দের অভিযোগ, জল নামছে না।",
            type="event",
            audio_intent="soundbite",
        ),
        NarrationSegment(
            id="narration_02",
            start=5.0,
            end=9.0,
            text="রাস্তায় যান চলাচল ব্যাহত।",
            type="event",
            audio_intent="script",
        ),
    ]
    plan = TimelinePlan(
        headline="বীরভানপুর",
        duration=9.0,
        timeline=[
            _clip(0, 5, "clip01.mov", "narration_01"),
            _clip(5, 9, "clip03.mov", "narration_02"),
        ],
    )
    segments = [
        _audio(
            id="audio_clip02_01",
            source_file="clip02.mov",
            start=14.0,
            end=20.0,
            contains_speech=True,
            transcript="",
            speaker_type="on_camera",
            audio_type="soundbite",
            speech_quality=0.7,
            information_value=0.55,
            news_relevance=0.4,
            rms=0.08,
            peak=0.5,
            playback_gain=1.0,
        )
    ]
    alignment = AlignmentResult(
        duration=9.0,
        cues=[CaptionCue(start=0, end=5, text=narration[0].text), CaptionCue(start=5, end=9, text=narration[1].text)],
    )
    result, debug = apply_audio_editorial(plan, narration, segments, alignment, get_settings())
    modes = [clip.audio.mode for clip in result.timeline]
    assert modes[0] == "VOICEOVER_ONLY"
    assert modes[1] == "SOURCE_SOUNDBITE"
    assert result.timeline[1].source == "clip02.mov"
    assert result.timeline[1].audio.voice_volume == 0
    assert result.timeline[1].audio.source_volume > 0
    assert result.timeline[2].audio.mode == "VOICEOVER_ONLY"
    assert result.timeline[2].audio.source_volume == 0
    assert debug[0].action == "INSERT_AFTER"


def test_script_cues_decide_when_to_throw_to_field_voice() -> None:
    assert _audio_intent("দুর্গাপুর: টানা বৃষ্টিতে জলমগ্ন বীরভানপুর।", "hook") == "script"
    assert _audio_intent("একাধিক বাড়ির উঠোন পেরিয়ে জল ঢুকেছে ঘরের ভিতরেও।", "event") == "script"
    assert _audio_intent("দিনের পর দিন জল জমে থাকায় সমস্যায় পড়েছেন বাসিন্দারা।", "event") == "script"
    assert _audio_intent("স্থানীয়দের অভিযোগ, নিকাশি ব্যবস্থা বেহাল।", "event") == "soundbite"
    assert _audio_intent("একাধিকবার প্রশাসনকে জানানো হলেও সমাধান হয়নি বলে দাবি তাঁদের।", "quote") == "soundbite"
    assert _audio_intent("জল সমস্যার দ্রুত সমাধানের দাবিতে সরব হন তাঁরা।", "event") == "soundbite"
    assert _audio_intent("বাঁকুড়া-দুর্গাপুর সড়কে যান চলাচল ব্যাহত হয়।", "event") == "script"
    assert _audio_intent("দ্রুত সমাধান না হলে বৃহত্তর আন্দোলনের হুঁশিয়ারি দিয়েছেন বিক্ষোভকারীরা।", "close") == "soundbite"
