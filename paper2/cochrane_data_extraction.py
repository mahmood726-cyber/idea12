"""
Paper #2: Cochrane Review Data Extraction and ML Model
Predicting Medical Reversals Using Machine Learning

This script:
1. Loads 25 validated cases from Paper #1 (training data)
2. Provides template for extracting Cochrane review data
3. Calculates forensic metrics (DI, E-value, Inflation)
4. Trains ML models (Logistic Regression, Random Forest, XGBoost)
5. Applies model to new Cochrane reviews
6. Generates risk scores and predictions
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut, cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, roc_curve, classification_report
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

# Add parent directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import forensic analyzer
import importlib.util
spec = importlib.util.spec_from_file_location(
    "bias_detector",
    os.path.join(os.path.dirname(__file__), '..', 'netmetareg', 'forensic', 'bias_detector.py')
)
bias_detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bias_detector)
ForensicAnalyzer = bias_detector.ForensicAnalyzer


class CochraneMLPipeline:
    """Complete ML pipeline for predicting medical reversals"""

    def __init__(self):
        self.training_data = None
        self.models = {}
        self.best_model = None
        self.feature_names = []
        self.scaler = StandardScaler()

    def load_paper1_training_data(self):
        """Load 25 validated cases from Paper #1 as training data"""

        print("Loading training data from Paper #1 validation...")

        # Load from medical_reversal_results_N25.csv
        results_file = os.path.join(
            os.path.dirname(__file__),
            '..',
            'validation',
            'results',
            'medical_reversal_results_N25.csv'
        )

        if os.path.exists(results_file):
            df = pd.read_csv(results_file)
            print(f"Loaded {len(df)} cases from validation results")

            # Create binary labels: Reversal=1, Concordant=0
            df['Label'] = (df['Type'] == 'REVERSAL').astype(int)

            self.training_data = df
            return df
        else:
            print(f"Error: {results_file} not found")
            print("Please run medical_reversal_validation.py first")
            return None

    def calculate_additional_features(self, df):
        """Calculate derived features for ML model"""

        print("Calculating additional ML features...")

        # Already have: DI, E_Value, Inflation

        # Add derived features
        df['DI_E_ratio'] = df['DI'] / df['E_Value'].fillna(1)
        df['Effect_magnitude_ratio'] = df['Obs_HR'] / df['RCT_HR']
        df['Effect_direction_match'] = ((df['Obs_HR'] < 1) == (df['RCT_HR'] < 1)).astype(int)

        # Log transformations for skewed features
        df['log_DI'] = np.log(df['DI'] + 0.1)  # Add small constant to avoid log(0)
        df['log_E_value'] = np.log(df['E_Value'].fillna(1))
        df['log_Inflation'] = np.log(df['Inflation'].fillna(1))

        # Domain encoding (if available)
        if 'Domain' in df.columns:
            domain_dummies = pd.get_dummies(df['Domain'], prefix='Domain')
            df = pd.concat([df, domain_dummies], axis=1)

        return df

    def prepare_features(self, df):
        """Prepare feature matrix for ML"""

        # Core features
        feature_cols = ['DI', 'E_Value', 'Inflation', 'DI_E_ratio',
                       'Effect_magnitude_ratio', 'Effect_direction_match',
                       'log_DI', 'log_E_value', 'log_Inflation']

        # Add domain features if available
        domain_cols = [col for col in df.columns if col.startswith('Domain_')]
        feature_cols.extend(domain_cols)

        # Filter to available columns
        feature_cols = [col for col in feature_cols if col in df.columns]

        self.feature_names = feature_cols

        # Handle missing values
        X = df[feature_cols].fillna(0)

        return X

    def train_models(self):
        """Train multiple ML models with cross-validation"""

        if self.training_data is None:
            print("No training data loaded. Run load_paper1_training_data() first.")
            return

        print("\n" + "="*80)
        print("TRAINING ML MODELS ON 25 VALIDATED CASES")
        print("="*80)

        # Prepare data
        df = self.calculate_additional_features(self.training_data)
        X = self.prepare_features(df)
        y = df['Label'].values

        print(f"\nFeatures: {self.feature_names}")
        print(f"Training samples: {len(X)} (Reversals: {y.sum()}, Concordant: {(1-y).sum()})")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Define models
        models = {
            'Logistic Regression': LogisticRegression(penalty='l2', C=1.0, max_iter=1000, random_state=42),
            'Random Forest': RandomForestClassifier(n_estimators=100, max_depth=5,
                                                   min_samples_split=3, random_state=42),
        }

        # Add XGBoost if available
        try:
            import xgboost as xgb
            models['XGBoost'] = xgb.XGBClassifier(n_estimators=100, max_depth=3,
                                                 learning_rate=0.1, random_state=42)
        except ImportError:
            print("XGBoost not available, skipping...")

        # Cross-validation
        print("\n" + "-"*80)
        print("CROSS-VALIDATION RESULTS (Leave-One-Out)")
        print("-"*80)

        loo = LeaveOneOut()

        for name, model in models.items():
            # LOO cross-validation
            scores = cross_val_score(model, X_scaled, y, cv=loo, scoring='roc_auc')

            print(f"\n{name}:")
            print(f"  ROC AUC: {scores.mean():.3f} ± {scores.std():.3f}")

            # Train on full dataset for predictions
            model.fit(X_scaled, y)

            # Predictions
            y_pred_proba = model.predict_proba(X_scaled)[:, 1]
            y_pred = (y_pred_proba > 0.5).astype(int)

            # Metrics
            print(f"  Training accuracy: {(y_pred == y).mean():.1%}")
            print(f"  Sensitivity: {((y_pred == 1) & (y == 1)).sum() / y.sum():.1%}")
            print(f"  Specificity: {((y_pred == 0) & (y == 0)).sum() / (1-y).sum():.1%}")

            # Store model
            self.models[name] = model

        # Select best model (highest CV AUC)
        best_name = max(models.keys(),
                       key=lambda x: cross_val_score(self.models[x], X_scaled, y, cv=loo, scoring='roc_auc').mean())
        self.best_model = self.models[best_name]

        print(f"\n" + "="*80)
        print(f"BEST MODEL: {best_name}")
        print("="*80)

        return self.models

    def get_feature_importance(self, model_name='Random Forest'):
        """Get feature importance from trained model"""

        if model_name not in self.models:
            print(f"Model {model_name} not found")
            return None

        model = self.models[model_name]

        # Feature importance
        if hasattr(model, 'feature_importances_'):
            importance = pd.DataFrame({
                'Feature': self.feature_names,
                'Importance': model.feature_importances_
            }).sort_values('Importance', ascending=False)

            print(f"\n{model_name} - Feature Importance:")
            print(importance.to_string(index=False))

            return importance
        else:
            print(f"{model_name} does not have feature_importances_")
            return None

    def predict_cochrane_review(self, obs_hr, obs_ci_lower, obs_ci_upper, obs_n,
                                rct_hr, rct_ci_lower, rct_ci_upper, rct_n,
                                domain=None):
        """
        Predict reversal risk for a new Cochrane review

        Parameters:
        -----------
        obs_hr : float
            Observational pooled hazard ratio
        obs_ci_lower : float
            Observational 95% CI lower bound
        obs_ci_upper : float
            Observational 95% CI upper bound
        obs_n : int
            Observational total sample size
        rct_hr : float
            RCT pooled hazard ratio
        rct_ci_lower : float
            RCT 95% CI lower bound
        rct_ci_upper : float
            RCT 95% CI upper bound
        rct_n : int
            RCT total sample size
        domain : str, optional
            Clinical domain

        Returns:
        --------
        dict : Prediction results with risk score
        """

        if self.best_model is None:
            print("No trained model available. Run train_models() first.")
            return None

        # Calculate forensic metrics
        obs_se = (np.log(obs_ci_upper) - np.log(obs_ci_lower)) / (2 * 1.96)
        rct_se = (np.log(rct_ci_upper) - np.log(rct_ci_lower)) / (2 * 1.96)

        obs_data = pd.DataFrame({
            'study': ['Obs_Meta'],
            'effect': [np.log(obs_hr)],
            'se': [obs_se],
            'n': [obs_n]
        })

        rct_data = pd.DataFrame({
            'study': ['RCT_Meta'],
            'effect': [np.log(rct_hr)],
            'se': [rct_se],
            'n': [rct_n]
        })

        # Run forensic analysis
        try:
            analyzer = ForensicAnalyzer(obs_data, rct_data, effect_type='log_hr', rare_outcome=False)
            results = analyzer.analyze()

            # Build feature vector
            features = {
                'DI': results.discordance_index,
                'E_Value': results.e_value_point,
                'Inflation': results.inflation_factor,
                'DI_E_ratio': results.discordance_index / results.e_value_point,
                'Effect_magnitude_ratio': obs_hr / rct_hr,
                'Effect_direction_match': int((obs_hr < 1) == (rct_hr < 1)),
                'log_DI': np.log(results.discordance_index + 0.1),
                'log_E_value': np.log(results.e_value_point),
                'log_Inflation': np.log(results.inflation_factor)
            }

            # Add domain encoding if provided
            if domain is not None:
                for col in self.feature_names:
                    if col.startswith('Domain_'):
                        features[col] = 1 if col == f'Domain_{domain}' else 0

            # Fill missing features with 0
            for col in self.feature_names:
                if col not in features:
                    features[col] = 0

            # Create feature vector in correct order
            X_new = np.array([[features[col] for col in self.feature_names]])

            # Scale features
            X_new_scaled = self.scaler.transform(X_new)

            # Predict
            risk_score = self.best_model.predict_proba(X_new_scaled)[0, 1]
            prediction = "HIGH RISK" if risk_score > 0.7 else "MODERATE RISK" if risk_score > 0.4 else "LOW RISK"

            # Results
            prediction_results = {
                'Risk_Score': risk_score,
                'Risk_Percentage': f"{risk_score*100:.1f}%",
                'Prediction': prediction,
                'DI': results.discordance_index,
                'Grade': results.evidence_grade,
                'E_Value': results.e_value_point,
                'Inflation': results.inflation_factor,
                'Obs_HR': obs_hr,
                'RCT_HR': rct_hr
            }

            return prediction_results

        except Exception as e:
            print(f"Error in prediction: {e}")
            return None

    def batch_predict_cochrane_reviews(self, reviews_df):
        """
        Predict for multiple Cochrane reviews

        Parameters:
        -----------
        reviews_df : pd.DataFrame
            DataFrame with columns: obs_hr, obs_ci_lower, obs_ci_upper, obs_n,
                                   rct_hr, rct_ci_lower, rct_ci_upper, rct_n, domain

        Returns:
        --------
        pd.DataFrame : Predictions for all reviews
        """

        predictions = []

        print(f"\nPredicting for {len(reviews_df)} Cochrane reviews...")

        for idx, row in reviews_df.iterrows():
            result = self.predict_cochrane_review(
                obs_hr=row['obs_hr'],
                obs_ci_lower=row['obs_ci_lower'],
                obs_ci_upper=row['obs_ci_upper'],
                obs_n=row['obs_n'],
                rct_hr=row['rct_hr'],
                rct_ci_lower=row['rct_ci_lower'],
                rct_ci_upper=row['rct_ci_upper'],
                rct_n=row['rct_n'],
                domain=row.get('domain', None)
            )

            if result:
                result['Review_ID'] = row.get('review_id', idx)
                result['Title'] = row.get('title', 'Unknown')
                predictions.append(result)

        predictions_df = pd.DataFrame(predictions)

        # Sort by risk score
        predictions_df = predictions_df.sort_values('Risk_Score', ascending=False)

        # Summary
        print(f"\nPREDICTION SUMMARY:")
        print(f"  High Risk (>70%): {(predictions_df['Risk_Score'] > 0.7).sum()}")
        print(f"  Moderate Risk (40-70%): {((predictions_df['Risk_Score'] > 0.4) & (predictions_df['Risk_Score'] <= 0.7)).sum()}")
        print(f"  Low Risk (<40%): {(predictions_df['Risk_Score'] <= 0.4).sum()}")

        return predictions_df


# Example usage
if __name__ == "__main__":

    print("="*80)
    print("PAPER #2: ML-BASED PREDICTION OF MEDICAL REVERSALS")
    print("="*80)

    # Initialize pipeline
    pipeline = CochraneMLPipeline()

    # Load training data from Paper #1
    training_data = pipeline.load_paper1_training_data()

    if training_data is not None:
        # Train models
        pipeline.train_models()

        # Feature importance
        pipeline.get_feature_importance('Random Forest')

        # Example prediction for a new Cochrane review
        print("\n" + "="*80)
        print("EXAMPLE: Predicting New Cochrane Review")
        print("="*80)
        print("\nScenario: Hypothetical review comparing obs vs RCT for new intervention")
        print("  Observational: HR=0.70 (95% CI: 0.60-0.82), N=10,000")
        print("  RCT: HR=0.95 (95% CI: 0.82-1.10), N=2,000")

        example_prediction = pipeline.predict_cochrane_review(
            obs_hr=0.70,
            obs_ci_lower=0.60,
            obs_ci_upper=0.82,
            obs_n=10000,
            rct_hr=0.95,
            rct_ci_lower=0.82,
            rct_ci_upper=1.10,
            rct_n=2000,
            domain='Cardiology'
        )

        if example_prediction:
            print(f"\nPREDICTION RESULTS:")
            print(f"  Risk Score: {example_prediction['Risk_Percentage']}")
            print(f"  Classification: {example_prediction['Prediction']}")
            print(f"  Discordance Index: {example_prediction['DI']:.2f}")
            print(f"  Evidence Grade: {example_prediction['Grade']}")
            print(f"  E-Value: {example_prediction['E_Value']:.2f}")
            print(f"\nINTERPRETATION:")
            if example_prediction['Risk_Score'] > 0.7:
                print("  HIGH RISK of medical reversal - observational evidence likely biased")
                print("  Recommendation: Do NOT pool designs, trust RCT evidence")
            elif example_prediction['Risk_Score'] > 0.4:
                print("  MODERATE RISK - investigate heterogeneity and potential confounding")
                print("  Recommendation: Caution advised, await additional RCT evidence")
            else:
                print("  LOW RISK - designs concordant, pooling may be appropriate")
                print("  Recommendation: Careful pooling with sensitivity analysis")

        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Extract data from 100-501 Cochrane reviews")
        print("2. Apply trained model to all reviews")
        print("3. Identify high-risk reviews (>70% probability)")
        print("4. Map to current clinical guidelines")
        print("5. Write Paper #2 manuscript for Lancet/JAMA")
        print("\nSee PAPER_2_DATA_COLLECTION_PLAN.md for detailed workflow")
