# %%
import pandas as pd
import glob
import json
import matplotlib.pyplot as plt

# %%
files = glob.glob('data/202507-citibike-tripdata/*.csv')
files

# %%
clean_chunks = []

for f in files:
    for chunk in pd.read_csv(
        f,
        chunksize=200000,
        low_memory=False,
        dtype={'start_station_id': 'string', 'end_station_id': 'string'}
    ):
        chunk['started_at'] = pd.to_datetime(chunk['started_at'], errors='coerce')
        chunk['ended_at'] = pd.to_datetime(chunk['ended_at'], errors='coerce')
        chunk = chunk.dropna(subset=['started_at','ended_at'])
        d = (chunk['ended_at'] - chunk['started_at']).dt.total_seconds()
        chunk = chunk[(d >= 60) & (d <= 10800)]
        chunk = chunk[(chunk['started_at'].dt.year == 2025) & (chunk['started_at'].dt.month == 7)]
        chunk['date'] = chunk['started_at'].dt.date
        chunk['hour'] = chunk['started_at'].dt.hour
        clean_chunks.append(chunk)

trips_clean = pd.concat(clean_chunks, ignore_index=True)

# %%
with open("data/NYC_Weather_July2025.txt") as f:
    weather_json = json.load(f)

# %%
weather_days = weather_json['days']
weather_rows = []

for day in weather_days:
    date = day['datetime']
    for h in day['hours']:
        weather_rows.append({
            'date': date,
            'hour': int(h['datetime'].split(':')[0]),
            'temp': h['temp'],
            'feelslike': h['feelslike'],
            'precip': h['precip'],
            'cloudcover': h['cloudcover'],
            'conditions': h['conditions']
        })

weather = pd.DataFrame(weather_rows)
weather['date'] = pd.to_datetime(weather['date']).dt.date

# %%
merged = trips_clean.merge(weather, on=['date','hour'], how='left')

merged_trips = trips_clean.merge(weather, on=['date','hour'], how='left')

rides_by_hour = (
    trips_clean
    .groupby(['date','hour'])
    .size()
    .reset_index(name='rides')
)

merged_hourly = rides_by_hour.merge(weather, on=['date','hour'], how='left')

# %%
merged.head()

# %%
counts = trips_clean['member_casual'].value_counts()

plt.figure(figsize=(7,5))
plt.bar(counts.index, counts.values)
plt.xlabel("Rider Type")
plt.ylabel("Number of Trips")
plt.title("Member vs Casual Riders — July 2025")
plt.tight_layout()
plt.show()

# %%
types = trips_clean['rideable_type'].value_counts()

plt.figure(figsize=(7,5))
plt.bar(types.index, types.values)
plt.xlabel("Bike Type")
plt.ylabel("Number of Trips")
plt.title("Rideable Type Distribution — July 2025")
plt.tight_layout()
plt.show()

# %%
hourly_avg = (
    trips_clean
    .groupby(['date','hour'])
    .size()
    .groupby('hour')
    .mean()
)

# %%
hourly_stats = merged_hourly.groupby('hour')['rides'].agg(['mean','std']).reset_index()

plt.figure(figsize=(12,6))

plt.plot(hourly_stats['hour'], hourly_stats['mean'], color='blue', linewidth=2, label='Average Rides')

plt.fill_between(
    hourly_stats['hour'],
    hourly_stats['mean'] - hourly_stats['std'],
    hourly_stats['mean'] + hourly_stats['std'],
    color='blue',
    alpha=0.2,
    label='±1 Standard Deviation'
)

plt.title("Average Rides Per Day by Hour")
plt.xlabel("Hour of Day (0–23)")
plt.ylabel("Average Number of Rides")
plt.legend()
plt.grid(alpha=0.3)

plt.show()

# %%
hourly_member = (
    merged_trips[merged_trips['member_casual'] == 'member']
    .groupby('hour')
    .size()
)

hourly_casual = (
    merged_trips[merged_trips['member_casual'] == 'casual']
    .groupby('hour')
    .size()
)

plt.figure(figsize=(10,5))
plt.plot(hourly_member.index, hourly_member.values, label='Member')
plt.plot(hourly_casual.index, hourly_casual.values, label='Casual')
plt.xlabel("Hour of Day")
plt.ylabel("Number of Trips")
plt.title("Hourly Ridership: Members vs Casual Riders — July 2025")
plt.legend()
plt.tight_layout()
plt.show()

# %%
merged_trips['started_at'] = pd.to_datetime(merged_trips['started_at'])
merged_trips['weekday'] = merged_trips['started_at'].dt.dayofweek < 5

merged_trips[['started_at','weekday']].head()

# %%
merged_hourly = merged_trips.groupby(['date','hour','weekday']).agg({
    'ride_id':'count',
    'temp':'mean',
    'feelslike':'mean',
    'precip':'mean',
    'cloudcover':'mean'
}).reset_index()

merged_hourly = merged_hourly.rename(columns={'ride_id':'rides'})

# %%
t = merged_trips.copy()
t['date'] = t['started_at'].dt.date
t['hour'] = t['started_at'].dt.hour
t['weekday'] = t['started_at'].dt.weekday < 5

g = t.groupby(['weekday','date','hour'])['ride_id'].size().reset_index(name='rides')
g = g.groupby(['weekday','hour'])['rides'].agg(['mean','std']).reset_index()

wd = g[g['weekday'] == True]
we = g[g['weekday'] == False]

plt.figure(figsize=(10,5))

# Weekday
plt.plot(wd['hour'], wd['mean'], label='Weekday')
plt.fill_between(wd['hour'], wd['mean'] - wd['std'], wd['mean'] + wd['std'],
                 alpha=.2, label='±1 Sd (Weekday)')

# Weekend
plt.plot(we['hour'], we['mean'], label='Weekend')
plt.fill_between(we['hour'], we['mean'] - we['std'], we['mean'] + we['std'],
                 alpha=.2, label='±1 Sd (Weekend)')

plt.xlabel('Hour of Day (0–23)')
plt.ylabel('Average Number of Rides')
plt.title('Average Rides Per Day by Hour: Weekday vs Weekend')
plt.legend()
plt.tight_layout()
plt.show()

# %%
merged_trips['day_type'] = merged_trips['weekday'].map({
    True: 'Weekday',
    False: 'Weekend'
})

c = merged_trips.groupby(['day_type','member_casual'])['ride_id'].count()
c = c.groupby(level=0).apply(lambda x: x / x.sum())
c = c.unstack()

c.plot(kind='barh', stacked=True)
plt.xlabel('Proportion of Rides')
plt.ylabel('Day Type')
plt.title('Member vs Casual Share')
plt.show()

# %%
print("merged_trips shape:", merged_trips.shape)
display(merged_trips.head())

# %%
print("merged_hourly shape:", merged_hourly.shape)
display(merged_hourly.head())

# %%
merged_hourly[['rides','temp','feelslike','precip','cloudcover']].corr()

# %%
from sklearn.linear_model import LinearRegression

X = merged_hourly[['temp','precip','cloudcover']]
y = merged_hourly['rides']

model = LinearRegression()
model.fit(X, y)

intercept = model.intercept_
coef = model.coef_

print(f"Intercept: {intercept:.2f}")
print(f"temp: {coef[0]:.2f}")
print(f"precip: {coef[1]:.2f}")
print(f"cloudcover: {coef[2]:.2f}")

# %%
print("Temperature has a strong positive effect on ridership, meaning warmer hours consistently lead to more rides. Precipitation shows a large negative coefficient, \nindicating that rainfall reduces ridership, although the effect can vary depending on intensity and duration. Cloud cover has a small positive effect, \nsuggesting that overcast conditions slightly increase ridership, possibly because riders avoid direct sun or heat. Overall, the model shows how \ndifferent weather factors contribute to changes in hourly ride volume.")

# %%
rain_hours = merged_hourly['precip'].gt(0).sum()
total_hours = merged_hourly.shape[0]
rain_hours / total_hours

# %%
merged_trips.groupby(['member_casual', 'cloudcover'])['ride_id'].count().unstack()

# %%
merged_trips['cloud_bin'] = pd.cut(
    merged_trips['cloudcover'],
    bins=[0,30,70,100],
    labels=['Clear','Partly Cloudy','Overcast']
)

merged_trips.groupby(['cloud_bin','member_casual'])['ride_id'].count().unstack()

# %%
cloud_prop = merged_trips.groupby(['cloud_bin','member_casual'])['ride_id'].count()
cloud_prop = cloud_prop.groupby(level=0).apply(lambda x: x / x.sum())
cloud_prop.unstack()


# %%
import seaborn as sns
temp_curve = merged_hourly.groupby('temp')['rides'].mean().reset_index()
sns.lineplot(data=temp_curve, x='temp', y='rides')
plt.title('Temperature vs Average Hourly Ridership')
plt.show()

# %%
feels_curve = merged_hourly.groupby('feelslike')['rides'].mean().reset_index()
sns.lineplot(data=feels_curve, x='feelslike', y='rides')
plt.title('Feels-Like Temperature vs Average Hourly Ridership')
plt.show()

# %%
hourly_by_type = trips_clean.groupby(['date','hour','member_casual']).size().reset_index(name='rides')

# %%
merged_type_weather = hourly_by_type.merge(weather, on=['date','hour'], how='left')

# %%
casual = merged_type_weather[merged_type_weather['member_casual'] == 'casual']
member = merged_type_weather[merged_type_weather['member_casual'] == 'member']

casual_corr = casual[['rides','temp','feelslike','precip','cloudcover']].corr()['rides']
member_corr = member[['rides','temp','feelslike','precip','cloudcover']].corr()['rides']

casual_corr, member_corr

# %%
merged_hourly['period'] = merged_hourly['hour'].apply(
    lambda h: 'commute' if h in [7,8,9,16,17,18] else 'midday'
)

# %%
commute = merged_hourly[merged_hourly['period'] == 'commute']
midday = merged_hourly[merged_hourly['period'] == 'midday']

commute_corr = commute[['rides','temp','feelslike','precip','cloudcover']].corr()['rides']
midday_corr = midday[['rides','temp','feelslike','precip','cloudcover']].corr()['rides']

commute_corr, midday_corr

# %%
df = merged_hourly.copy()

# %%
df_test = df.merge(
    merged_trips[['date','hour','member_casual']],
    on=['date','hour'],
    how='left'
)

# %%
import scipy.stats as stats
import pandas as pd

table = pd.crosstab(df_test['cloudcover'], df_test['member_casual'])
chi2, p, dof, expected = stats.chi2_contingency(table)
p

# %%
from scipy.stats import pearsonr

pearsonr(df['temp'], df['rides'])
pearsonr(df['feelslike'], df['rides'])

# %%
from scipy.stats import pearsonr
pearsonr(df['precip'], df['rides'])

# %%
from scipy.stats import pearsonr
pearsonr(df['cloudcover'], df['rides'])


# %%
df = merged_hourly.copy()

# %%
from scipy.stats import norm
from math import atanh, sqrt

def fisher_compare(r1, r2, n1, n2):
    z1 = atanh(r1)
    z2 = atanh(r2)
    se = sqrt(1/(n1-3) + 1/(n2-3))
    z = (z1 - z2) / se
    p = 2 * (1 - norm.cdf(abs(z)))
    return z, p

df_casual = merged_trips[merged_trips['member_casual'] == 'casual']
df_member = merged_trips[merged_trips['member_casual'] == 'member']

n_casual = len(df_casual)
n_member = len(df_member)

corr = {
    "temp": (0.4871, 0.4806),
    "feelslike": (0.4506, 0.4670),
    "precip": (-0.0750, -0.0582),
    "cloudcover": (-0.0118, 0.0093)
}

for var, (r1, r2) in corr.items():
    z, p = fisher_compare(r1, r2, n_casual, n_member)
    print(var, z, p)

# %%
from math import atanh, sqrt
from scipy.stats import norm

def fisher_compare(r1, r2, n1, n2):
    z1 = atanh(r1)
    z2 = atanh(r2)
    se = sqrt(1/(n1-3) + 1/(n2-3))
    z = (z1 - z2) / se
    p = 2 * (1 - norm.cdf(abs(z)))
    return z, p

df_commute = df[df['period'] == 'commute']
df_midday  = df[df['period'] == 'midday']

n_commute = len(df_commute)
n_midday  = len(df_midday)

variables = {
    "temp": (0.5764, 0.5336),
    "feelslike": (0.5896, 0.5019),
    "precip": (-0.1232, -0.0655),
    "cloudcover": (-0.1682, 0.0328)
}

for var, (r1, r2) in variables.items():
    z, p = fisher_compare(r1, r2, n_commute, n_midday)
    print(var, z, p)


