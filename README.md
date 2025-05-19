# Traffic Simulator

Ce projet simule le fonctionnement de feux de circulation à un carrefour de deux voies et la traversée de voitures, en utilisant la programmation concurrente en Python.

## Table des matières

* [Installation](#installation)
* [Structure du code](#structure-du-code)
* [Fonctionnalités principales](#fonctionnalités-principales)
* [Processus et synchronisation](#processus-et-synchronisation)

  * [1. Initialisation](#1-initialisation)
  * [2. Cycle des feux (`traffic_light_process`)](#2-cycle-des-feux-traffic_light_process)
  * [3. Comportement d’une voiture (`car_process`)](#3-comportement-dune-voiture-car_process)
  * [4. Contrôle de capacité (`can_cross`)](#4-contrôle-de-capacité-can_cross)
* [Bibliothèques utilisées](#bibliothèques-utilisées)
* [Conditions respectées](#conditions-respectées)

## Installation

1. Clonez le dépôt

2. Installez les dépendances (si nécessaire) :

   ```bash
   pip install -r requirements.txt
   ```
3. Lancez la simulation :

   ```bash
   python traffic_simulator.py
   ```

## Structure du code

* **`traffic_simulator.py`** : implémentation principale.
* **Classes clés** :

  * `Road` : représente une voie, contient la liste des voitures, l’état du feu, un `Lock` et une `Condition`.
  * `Car` : représente une voiture, avec son état et sa position.
* **Fonctions** :

  * `start_simulation()` : initialise et lance les threads.
  * `traffic_light_process(road)` : gère le cycle des feux pour une `Road`.
  * `car_process(car_id, road_num)` : simule l’arrivée, l’attente et la traversée d’une voiture.
  * `can_cross(road, car)` : vérifie si la voiture peut entrer dans l’intersection.
  * `update_display()` : redessine périodiquement l’interface.

## Fonctionnalités principales

* Gestion de deux types de scénarios :

  * **Cas 1** : strictement 1 voiture à la fois.
  * **Cas 2** : jusqu’à *k* voitures simultanées, avec distance de sécurité.
* Alternance automatique des feux (vert → jaune → rouge).
* Affichage graphique sur un canevas.
* Synchronisation via `Lock` et `Condition`.

## Processus et synchronisation

### 1. Initialisation

* Création de deux objets `Road` (une par voie) :

  * `road.lock` (`Lock`) protège l’accès à `road.cars`.
  * `road.condition` (`Condition`) permet aux voitures d’attendre et d’être notifiées.
  * `road.light_state` initialisé à `RED`.
* Lancement, via `start_simulation()`, de plusieurs threads :

  * Un thread par voiture (`car_process`).
  * Un thread pour chaque feu (`traffic_light_process`).
  * Un thread pour mettre à jour l’affichage (`update_display`).

### 2. Cycle des feux (`traffic_light_process`)

```python
while self.is_running:
    for road in [road1, road2]:
        with road.condition:
            road.light_state = GREEN
            road.condition.notify_all()
        time.sleep(LIGHT_DURATION)
        with road.condition:
            road.light_state = YELLOW
            road.condition.notify_all()
        time.sleep(1)
        with road.condition:
            road.light_state = RED
            road.condition.notify_all()
```

* Alterne les états : **VERT** → **JAUNE** (1 s) → **ROUGE**.
* `notify_all()` réveille toutes les voitures en attente pour réévaluer `can_cross()`.

### 3. Comportement d’une voiture (`car_process`)

```python
# Arrivée
with road.lock:
    road.cars.append(car)

# Attente
while car.state != "exited":
    with road.condition:
        if (road.light_state in (GREEN, YELLOW)) and can_cross(road, car):
            car.state = "crossing"
            break
        road.condition.wait()

# Traversée
start = time.time()
while time.time() - start < CAR_CROSSING_TIME:
    car.position += 0.1
    time.sleep(0.1)

# Sortie
with road.lock:
    road.cars.remove(car)
    car.state = "exited"
```

* **`condition.wait()`** : blocage tant que la voiture ne peut pas traverser.
* Passage à l’état `"crossing"` dès que les conditions sont réunies.
* Mise à jour de la position jusqu’à sortie.

### 4. Contrôle de capacité (`can_cross`)

* **Cas 1** :

  ```python
  return not any(c.state == "crossing" for c in road.cars)
  ```

  → Exclusion mutuelle stricte.

* **Cas 2** :

  ```python
  crossing = [c for c in road.cars if c.state == "crossing"]
  # 1) Distance minimale
  if crossing and car.position - crossing[-1].position < SAFE_DISTANCE/CANVAS_WIDTH:
      return False
  # 2) Limite k
  return len(crossing) < k
  ```

  → Distance de sécurité + limite de *k* voitures.

## Bibliothèques utilisées

* **`threading`** : threads, `Lock`, `Condition`.
* **`time`** : temporisation (simuler les durées).
* **`tkinter`** : interface graphique (canevas).

## Conditions respectées

1. **A** : Chaque voiture traverse le carrefour en un temps fini.
2. **B** : Les feux alternent vert ↔ rouge, chaque couleur est maintenue un temps fini.
3. **C** : À un instant donné, seules des voitures d’une même voie peuvent être dans le carrefour.

---

