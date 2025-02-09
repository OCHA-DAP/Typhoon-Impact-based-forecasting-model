import numpy as np
import random
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.metrics import f1_score
from xgboost import XGBClassifier
import os
from sklearn.feature_selection import RFECV
import pandas as pd
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
    KFold,
)


from xgboost.sklearn import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def xgb_regression_features(
    X,
    y,
    features,
    search_space,
    min_features_to_select,
    cv_splits,
    GS_score,
    objective,
    GS_randomized,
    GS_n_iter,
    verbose,
):

    cv_folds = KFold(n_splits=cv_splits, shuffle=True)

    xgb = XGBRegressor(objective=objective)

    selector = RFECV(xgb, step=1, cv=4, verbose=0, min_features_to_select=min_features_to_select,n_jobs=-3)

    if GS_randomized == True:
        regr = RandomizedSearchCV(
            selector,
            param_distributions=search_space,
            scoring=GS_score,
            cv=cv_folds,
            verbose=verbose,
            return_train_score=True,
            refit=True,
            n_iter=GS_n_iter,
        )
    else:
        regr = GridSearchCV(
            selector,
            param_grid=search_space,
            scoring=GS_score,
            cv=cv_folds,
            verbose=verbose,
            return_train_score=True,
            refit=True,
        )

    regr.fit(X, y)
    selected = list(regr.best_estimator_.support_)
    selected_features = [x for x, y in zip(features, selected) if y == True]
    selected_params = regr.best_params_

    return selected_features, selected_params


def xgb_regression_performance(
    df_train_list,
    df_test_list,
    y_var,
    features,
    search_space,
    cv_splits,
    objective,
    GS_score,
    GS_randomized,
    GS_n_iter,
    verbose,
):

    train_score_mae_list = []
    test_score_mae_list = []
    train_score_rmse_list = []
    test_score_rmse_list = []
    selected_params = []
    df_predicted = pd.DataFrame(columns=["year", "actual", "predicted"])

    for i in range(len(df_train_list)):

        print(f"Running for {i+1} out of a total of {len(df_train_list)}")

        train = df_train_list[i]
        test = df_test_list[i]

        x_train = train[features]
        y_train = train[y_var]

        x_test = test[features]
        y_test = test[y_var]

        cv_folds = KFold(n_splits=cv_splits, shuffle=True)

        steps = [
            ("xgb", XGBRegressor(objective=objective,n_jobs=-3)),
        ]

        pipe = Pipeline(steps, verbose=0)

        # Applying GridSearch or RandomizedGridSearch
        if GS_randomized == True:
            mod = RandomizedSearchCV(
                pipe,
                search_space,
                scoring=GS_score,
                cv=cv_folds,
                verbose=verbose,
                return_train_score=True,
                refit=True,
                n_iter=GS_n_iter,
            )
        else:
            mod = GridSearchCV(
                pipe,
                search_space,
                scoring=GS_score,
                cv=cv_folds,
                verbose=verbose,
                return_train_score=True,
                refit=True,
            )

        # Fitting the model on the full dataset
        xgb_fitted = mod.fit(x_train, y_train)
        results = xgb_fitted.cv_results_

        y_pred_train = xgb_fitted.predict(x_train)
        y_pred_test = xgb_fitted.predict(x_test)

        train_score_mae = mean_absolute_error(y_pred_train, y_train)
        test_score_mae = mean_absolute_error(y_pred_test, y_test)
        train_score_rmse = mean_squared_error(y_pred_train, y_train, squared=False)
        test_score_rmse = mean_squared_error(y_pred_test, y_test, squared=False)

        train_score_mae_list.append(train_score_mae)
        test_score_mae_list.append(test_score_mae)
        train_score_rmse_list.append(train_score_rmse)
        test_score_rmse_list.append(test_score_rmse)

        df_predicted_temp = pd.DataFrame(
            {"typhoon": test["typhoon"], "actual": y_test, "predicted": y_pred_test}
        )

        df_predicted = pd.concat([df_predicted, df_predicted_temp])

        selected_params.append(xgb_fitted.best_params_)

        print(f"Selected Parameters {xgb_fitted.best_params_}")
        print(f"Train score: {train_score_mae}")
        print(f"Test score: {test_score_mae}")

    return df_predicted, selected_params

