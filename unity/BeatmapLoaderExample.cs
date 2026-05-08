using System;
using UnityEngine;

public sealed class BeatmapLoaderExample : MonoBehaviour
{
    [SerializeField] private TextAsset beatmapJson;

    public BeatmapData Beatmap { get; private set; }

    private void Awake()
    {
        if (beatmapJson == null)
        {
            Debug.LogWarning("No beatmap JSON assigned.");
            return;
        }

        Beatmap = JsonUtility.FromJson<BeatmapData>(beatmapJson.text);
        Debug.Log($"Loaded beatmap with {Beatmap.events.Length} events at {Beatmap.analysis.bpm:0.##} BPM.");
    }
}

[Serializable]
public sealed class BeatmapData
{
    public string version;
    public SourceInfo source;
    public AnalysisInfo analysis;
    public BeatEvent[] events;
    public SectionInfo[] sections;
}

[Serializable]
public sealed class SourceInfo
{
    public string filename;
    public string sha256;
    public float duration_sec;
}

[Serializable]
public sealed class AnalysisInfo
{
    public float bpm;
    public string meter;
    public float confidence;
}

[Serializable]
public sealed class BeatEvent
{
    public string id;
    public float time_sec;
    public string type;
    public float strength;
    public float confidence;
    public string source;
    public bool edited;
}

[Serializable]
public sealed class SectionInfo
{
    public float time_sec;
    public string type;
}

