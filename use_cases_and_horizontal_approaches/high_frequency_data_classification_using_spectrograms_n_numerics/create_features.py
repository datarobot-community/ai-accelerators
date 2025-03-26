from helpers import create_spectrogram_image, generate_base64_image
import librosa
from librosa import decompose, feature
import numpy as np
import pandas as pd
from statsmodels.stats import descriptivestats


class Featurizer:
    """
    Class that compute features on a numpy array
    """

    def __init__(self, array=None, sr=22050, n_fft=2048, freqs=None):
        """
        Initialize the message parser, parsing the gram message information.
        :param gram_df: A list of outlog messages
        """

        self.sr = sr
        self.n_fft = n_fft
        self.freqs = freqs

        self.features = {}
        self.spec_features = {}

        if array is not None:
            self.S = np.abs(librosa.stft(array, n_fft=self.n_fft))
            self.spec_features.update(
                {"spectrogram": generate_base64_image(create_spectrogram_image(self.S, self.sr))}
            )

    def _calc_vector_features(self, vec, suffix=None):
        """
         Calculate numeric features on an array
        :param vec: a feature vector to reduce
        """
        if vec is None:
            return {}

        stats_to_compute = [
            "mean",
            "std_err",
            "ci",
            "std",
            "iqr",
            "iqr_normal",
            "mad",
            "mad_normal",
            "coef_var",
            "range",
            "max",
            "min",
            "skew",
            "kurtosis",
            "jarque_bera",
            "mode",
            "freq",
            "median",
        ]
        features = descriptivestats.describe(vec, stats=stats_to_compute)
        features = features[0]
        if suffix:
            features = self.add_suffix(features, suffix=suffix)
        return features

    @staticmethod
    def add_suffix(features, suffix):
        """
        Rename a feature vector to have a suffix
          :features: a feature vector to reduce
         returns: dictionary of features
        """
        if type(features) == pd.DataFrame or type(features) == pd.Series:
            features = dict(features)
        elif type(features) == list:
            features = {suffix + str(i): features[i] for i in range(len(features))}
        assert type(features) == dict
        features = {suffix + str(k): features[k] for k in features.keys()}
        return features

    def _create_all_spectral_features(self):
        """
        Create all spectral features
        Requires a spectrogram at with at least 3 rows
        returns: dictionary of features
        """
        # chroma features
        chroma_features = self._extract_chroma_features()
        self.features.update(chroma_features)

        if len(self.S) > 9:
            mfcc = self._extract_mfcc_feature_means(number_of_mfcc=128)
            self.features.update(mfcc)

        # Spectral Centroid
        feat_spectral_centroid = feature.spectral_centroid(S=self.S, freq=self.freqs)[0]
        feat_spectral_centroid = self._calc_vector_features(
            feat_spectral_centroid, suffix="spec_centroid_"
        )
        self.features.update(feat_spectral_centroid)

        feat_spectral_bandwidth = feature.spectral_bandwidth(S=self.S, freq=self.freqs)[0]
        feat_spectral_bandwidth = self._calc_vector_features(
            feat_spectral_bandwidth, suffix="spec_bandwidth_"
        )
        self.features.update(feat_spectral_bandwidth)

        feat_spectral_bandwidth_3 = feature.spectral_bandwidth(S=self.S, freq=self.freqs, p=3)[0]
        feat_spectral_bandwidth_3 = self._calc_vector_features(
            feat_spectral_bandwidth_3, suffix="spec_bandwidth_3_"
        )
        self.features.update(feat_spectral_bandwidth_3)

        feat_spectral_bandwidth_4 = feature.spectral_bandwidth(S=self.S, freq=self.freqs, p=4)[0]
        feat_spectral_bandwidth_4 = self._calc_vector_features(
            feat_spectral_bandwidth_4, suffix="spec_bandwidth_4_"
        )
        self.features.update(feat_spectral_bandwidth_4)

        feat_spectral_rolloff = feature.spectral_rolloff(S=self.S, freq=self.freqs)[0]
        feat_spectral_rolloff = self._calc_vector_features(
            feat_spectral_rolloff, suffix="feat_spectral_rolloff_"
        )
        self.features.update(feat_spectral_rolloff)

        feat_spectral_flatness = feature.spectral_flatness(S=self.S)[0]
        feat_spectral_flatness = self._calc_vector_features(
            feat_spectral_flatness, suffix="feat_spectral_flatness_"
        )
        self.features.update(feat_spectral_flatness)

        # compute the delta of the spectral centroid
        if len(self.S) > 9:
            feat_spectral_centroid_delta = feature.delta(
                feature.spectral_centroid(S=self.S, freq=self.freqs)[0]
            )
            feat_spectral_centroid_delta = self._calc_vector_features(
                feat_spectral_centroid_delta, suffix="feat_spectral_centroid_delta_"
            )
            self.features.update(feat_spectral_centroid_delta)

        return self.features

    def _create_all_spectrograms(self):
        # now lets get array features
        array_melspectrogram = feature.melspectrogram(S=self.S, sr=self.sr, n_fft=self.n_fft)
        self.spec_features.update(
            {
                "spectrogram_mel": generate_base64_image(
                    create_spectrogram_image(array_melspectrogram, self.sr)
                )
            }
        )

        h, p = decompose.hpss(S=self.S)
        self.spec_features.update(
            {"spectrogram_harmonic": generate_base64_image(create_spectrogram_image(h, self.sr))}
        )
        self.spec_features.update(
            {"spectrogram_percussive": generate_base64_image(create_spectrogram_image(p, self.sr))}
        )

        return self.spec_features

    def _extract_chroma_features(self):
        chroma = feature.chroma_stft(S=self.S, sr=self.sr, n_fft=self.n_fft)
        feat = {"chroma_" + str(i): np.mean(chroma[i]) for i in range(len(chroma))}

        return feat

    def _extract_mfcc_feature_means(self, number_of_mfcc=8):
        mfcc_alt = librosa.feature.mfcc(S=self.S, n_mfcc=number_of_mfcc)
        feat_1 = {"feat_mfcc_" + str(i): np.mean(mfcc_alt[i]) for i in range(len(mfcc_alt))}

        if min(self.S.shape[1], 9) >= 3:
            delta = librosa.feature.delta(mfcc_alt, width=min(self.S.shape[1], 9))
            feat_2 = {"feat_mfcc_delta_" + str(i): np.mean(delta[i]) for i in range(len(delta))}
            feat_1.update(feat_2)

            accelerate = librosa.feature.delta(mfcc_alt, order=2, width=min(self.S.shape[1], 9))
            feat_3 = {
                "feat_mfcc_accel_" + str(i): np.mean(accelerate[i]) for i in range(len(accelerate))
            }
            feat_1.update(feat_3)

        return feat_1
