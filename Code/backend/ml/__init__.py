# This package holds the ML layer: the trained model artifact
# (model.pkl, produced by scripts/train_model.py) and, as a follow-up
# step, the module that loads it into the live scoring engine.
#
# model.pkl is a build artifact, not source — add app/ml/model.pkl to
# .gitignore if this project is under version control.
