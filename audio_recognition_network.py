import os
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import seaborn as sns
import math

from tensorflow.keras.layers.experimental import preprocessing
from tensorflow.keras import layers
from tensorflow.keras import models
from IPython import display
import librosa


def decode_audio(audio_binary):
    audio, _ = tf.audio.decode_wav(audio_binary)
    return tf.squeeze(audio, axis=-1)


def get_label(file_path):
    parts = tf.strings.split(file_path, os.path.sep)
    return parts[-2]


def get_waveform_and_label(file_path):
    label = get_label(file_path)
    audio_binary = tf.io.read_file(file_path)
    waveform = decode_audio(audio_binary)
    return waveform, label


def get_spectrogram(waveform):
    zero_padding = tf.zeros([16000] - tf.shape(waveform), dtype=tf.float32)
    waveform = tf.cast(waveform, tf.float32)
    equal_length = tf.concat([waveform, zero_padding], 0)
    spectrogram = tf.signal.stft(equal_length, frame_length=255, frame_step=128)
    spectrogram = tf.abs(spectrogram)
    return spectrogram


def plot_spectrogram(spectrogram, ax):
    log_spec = np.log(spectrogram.T)
    height = log_spec.shape[0]
    width = log_spec.shape[1]
    x = np.linspace(0, np.size(spectrogram), num=width, dtype=int)
    y = range(height)
    ax.pcolormesh(x, y, log_spec, shading='auto')


def get_white_noise(signal,SNR) :
    #RMS value of signal
    RMS_s=math.sqrt(np.mean(signal**2))
    #RMS values of noise
    RMS_n=math.sqrt(RMS_s**2/(pow(10,SNR/10)))
    #Additive white gausian noise. Thereore mean=0
    #Because sample length is large (typically > 40000)
    #we can use the population formula for standard daviation.
    #because mean=0 STD=RMS
    STD_n=RMS_n
    noise=np.random.normal(0, STD_n, signal.shape[0])
    return noise


def to_polar(complex_ar):
    return np.abs(complex_ar),np.angle(complex_ar)

#https://github.com/sleekEagle/audio_processing
def get_noise_from_sound(signal, noise, SNR):
    RMS_s = math.sqrt(np.mean(signal ** 2))
    # required RMS of noise
    RMS_n = math.sqrt(RMS_s ** 2 / (pow(10, SNR / 10)))

    # current RMS of noise
    RMS_n_current = math.sqrt(np.mean(noise ** 2))
    noise = noise * (RMS_n / RMS_n_current)

    return noise


def run():
    seed = 23
    tf.random.set_seed(seed)
    np.random.seed(seed)

    data_dir = pathlib.Path('data/speech_commands')

    commands = np.array(tf.io.gfile.listdir(str(data_dir)))
    commands = commands[commands != 'README.md']

    filenames = tf.io.gfile.glob(str(data_dir) + '/*/*')
    filenames = tf.random.shuffle(filenames)
    num_samples = len(filenames)

    print('Number of total examples: ', num_samples)
    print('Number of examples per label: ', len(tf.io.gfile.listdir(str(data_dir / commands[0]))))
    print('Example file tensor: ', filenames[0])

    train_files = filenames[:30]
    val_files = filenames[30: 30 + 5]
    test_files = filenames[-2:]

    print('Training set size: ', len(train_files))
    print('Validation set size: ', len(val_files))
    print('Test set size: ', len(test_files))

    #https://github.com/sleekEagle/audio_processing

    # name = 'he.wav'
    # p1 = 'data\speech_commands\здравствуйте\\' + name
    # p2 = 'data\speech_commands\стоп\\' + name
    # p3 = 'data\speech_commands\неправильно\\' + name
    #
    # s_paths = list([p1, p2, p3])
    # signals = list()
    #
    # for i in range(len(s_paths)):
    #     path = s_paths[i]
    #     signal, sr = librosa.load(path)
    #     signal = np.interp(signal, (signal.min(), signal.max()), (-1, 1))
    #     noise = get_white_noise(signal, SNR=-20)
    #     signal_noise = signal + noise
    #     signals.append(signal_noise)
    #     plt.xlim([0, 16000])
    #     # plt.plot(signal)
    #     plt.plot(signal_noise)
    #     # plt.xlabel("Frequency (Hz)")
    #     # plt.ylabel("Amplitude")
    #     plt.show()


    autotune = tf.data.AUTOTUNE
    files_ds = tf.data.Dataset.from_tensor_slices(train_files)
    waveforms_ds = files_ds.map(get_waveform_and_label, num_parallel_calls=autotune)

    rows = 5
    cols = 4
    n = rows * cols
    fig, axes = plt.subplots(rows, cols, figsize=(10, 12))

    for i, (audio, label) in enumerate(waveforms_ds.take(n)):
        r = i // cols
        c = i % cols
        ax = axes[r][c]
        ax.plot(audio.numpy())
        ax.set_yticks(np.arange(-1.2, 1.2, 0.2))
        label = label.numpy().decode('utf-8')
        ax.set_title(label)

    plt.show()

    for waveform, label in waveforms_ds.take(1):
        label = label.numpy().decode('utf-8')
        spectrogram = get_spectrogram(waveform)
        print('Label: ', label)
        print('Waveform shape: ', waveform.shape)
        print('Spectrogram shape: ', spectrogram.shape)
        print('Audio playback')

        display.display(display.Audio(waveform, rate=1600))

        fig, axes = plt.subplots(2, figsize=(12, 8))
        timescale = np.arange(waveform.shape[0])
        axes[0].plot(timescale, waveform.numpy(), color='black')
        axes[0].set_title('Waveform')
        axes[0].set_xlim([0, 16000])
        plot_spectrogram(spectrogram.numpy(), axes[1])
        axes[1].set_title('Spectrogram')
        plt.show()

    def get_spectrogram_and_label_id(audio_in, label_in):
        spectrogram_inner = get_spectrogram(audio_in)
        spectrogram_inner = tf.expand_dims(spectrogram_inner, -1)
        label_id_in = tf.argmax(label_in == commands)
        return spectrogram_inner, label_id_in

    spectrogram_ds = waveforms_ds.map(
        get_spectrogram_and_label_id, num_parallel_calls=autotune)

    rows = 5
    cols = 4
    n = rows * cols
    fig, axes = plt.subplots(rows, cols, figsize=(10, 10))
    for i, (spectrogram, label_id) in enumerate(spectrogram_ds.take(n)):
        r = i // cols
        c = i % cols
        ax = axes[r][c]
        plot_spectrogram(np.squeeze(spectrogram.numpy()), ax)
        ax.set_title(commands[label_id.numpy()])
        ax.axis('off')

    plt.show()

    def preprocess_dataset(files):
        files_ds_in = tf.data.Dataset.from_tensor_slices(files)
        output_ds = files_ds.map(get_waveform_and_label, num_parallel_calls=autotune)
        output_ds = output_ds.map(get_spectrogram_and_label_id, num_parallel_calls=autotune)
        return output_ds

    train_ds = spectrogram_ds
    val_ds = preprocess_dataset(val_files)
    test_ds = preprocess_dataset(test_files)

    batch_size = 64
    train_ds = train_ds.batch(batch_size)
    val_ds = val_ds.batch(batch_size)

    train_ds = train_ds.cache().prefetch(autotune)
    val_ds = val_ds.cache().prefetch(autotune)

    for spectrogram, _ in spectrogram_ds.take(1):
        input_shape = spectrogram.shape
        print('Input shape: ', input_shape)

    num_labels = len(commands)

    norm_layer = preprocessing.Normalization()
    norm_layer.adapt(spectrogram_ds.map(lambda x, _: x))

    model = models.Sequential([
        layers.Input(shape=input_shape),
        preprocessing.Resizing(32, 32),
        norm_layer,
        layers.Conv2D(32, 3, activation='relu'),
        layers.Conv2D(64, 3, activation='relu'),
        layers.MaxPooling2D(),
        layers.Dropout(0.25),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(num_labels)
    ])

    model.summary()

    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=['accuracy']
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=10,
        callbacks=tf.keras.callbacks.EarlyStopping(verbose=1, patience=2)
    )

    metrics = history.history
    plt.plot(history.epoch, metrics['loss'], metrics['val_loss'])
    plt.legend(['loss', 'val_loss'])
    plt.show()

    test_audio = []
    test_labels = []

    for audio, label in test_ds:
        test_audio.append(audio.numpy())
        test_labels.append(label.numpy())

    test_audio = np.array(test_audio)
    test_labels = np.array(test_labels)

    y_pred = np.argmax(model.predict(test_audio), axis=1)
    y_true = test_labels

    test_acc = sum(y_pred == y_true) / len(y_true)
    print(f'Test set accuracy: {test_acc:.0%}')

    confusion_matrix = tf.math.confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(confusion_matrix, xticklabels=commands, yticklabels=commands, annot=True, fmt='g')
    plt.xlabel('Prediction')
    plt.ylabel('Labrl')
    plt.show()

    sample_file = data_dir / 'no/01bb6a2a_nohash_0.wav'
    sample_ds = preprocess_dataset([str(sample_file)])

    for spectrogram, label in sample_ds.batch(1):
        prediction = model(spectrogram)
        plt.bar(commands, tf.nn.softmax(prediction[0]))
        plt.title(f'Predictions for {commands[label[0]]}')
        plt.show()


if __name__ == "__main__":
    run()
