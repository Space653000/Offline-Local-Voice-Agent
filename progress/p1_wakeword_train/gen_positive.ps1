Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$root = "C:\0_JN1_Offline-Local-Voice-Agent\progress\p1_wakeword_train"

$wakePhrase = "嗨小助理"
$voices = @("Microsoft Hanhan Desktop", "Microsoft Yating", "Microsoft Zhiwei")
$rates = @(-3, -1, 0, 1, 3)

$i = 0
foreach ($voice in $voices) {
    $synth.SelectVoice($voice)
    foreach ($rate in $rates) {
        $synth.Rate = $rate
        $i++
        $out = "$root\positive\pos_$i.wav"
        $synth.SetOutputToWaveFile($out)
        $synth.Speak($wakePhrase)
        $synth.SetOutputToNull()
    }
}
Write-Host "positive: generated $i files"

# 保留幾組當作 held-out 測試集（用完全沒在訓練集出現過的 rate 值）
$testRates = @(-4, 4)
$j = 0
foreach ($voice in $voices) {
    $synth.SelectVoice($voice)
    foreach ($rate in $testRates) {
        $synth.Rate = $rate
        $j++
        $out = "$root\test_positive\testpos_$j.wav"
        $synth.SetOutputToWaveFile($out)
        $synth.Speak($wakePhrase)
        $synth.SetOutputToNull()
    }
}
Write-Host "test_positive: generated $j files"

# 近似混淆詞（發音相近但不是喚醒詞本身）當作困難負樣本
$confusers = @("嗨小主理", "嗨小主任", "還小助理", "嗨曉助理", "海小助理", "嗨小組理")
$k = 0
foreach ($voice in $voices) {
    $synth.SelectVoice($voice)
    $synth.Rate = 0
    foreach ($c in $confusers) {
        $k++
        $out = "$root\negative\confuser_$k.wav"
        $synth.SetOutputToWaveFile($out)
        $synth.Speak($c)
        $synth.SetOutputToNull()
    }
}
Write-Host "confuser negatives: generated $k files"
